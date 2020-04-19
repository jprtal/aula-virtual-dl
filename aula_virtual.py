#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2018 Aitor Alonso at aalonso@aalonso.eu
# Copyright (C) 2020 Jorge Portal
# This script is under MIT license
#
# Version: 2020.04.19-0
# You can find new versions and fixes of this script over the time at
# https://github.com/jprtal/aula-virtual-dl

import argparse
import cgi
import concurrent.futures
import getpass
import os
import re
import shutil
from urllib.parse import unquote

import keyring
import requests
from bs4 import BeautifulSoup
from pathvalidate import sanitize_filename


def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("-r", "--route", help="location to download")
    parser.add_argument("-u", "--user", help="user")
    parser.add_argument("-s", "--size", help="maximum file size in MB")
    parser.add_argument("-c", "--course", help="course name")
    parser.add_argument("-o", "--overwrite", action="store_true", help="overwrite existing files")
    parser.add_argument("-w", "--workers", help="number of workers")

    return parser.parse_args()


def setup_browser():
    headers = [("User-agent",
                "Mozilla/5.0 (X11; Linux x86_64; rv:75.0) Gecko/20100101 Firefox/75.0")]

    session = requests.Session()

    session.headers.update(headers)

    return session


def get_keyring_password(username):
    try:
        keyring_password = keyring.get_password("aula-virtual-dl", username)
    except keyring.errors.InitError:
        keyring_password = None
        print("Failed to initialize keyring\n")

    return keyring_password


def get_credentials(args):
    if args.user is not None:
        user = args.user
    else:
        user = input("Enter user: ")

    # Check if password was previously stored
    password = get_keyring_password(user)

    if password is None:
        prompt_save = True
        password = getpass.getpass(prompt="Enter password: ")
    else:
        prompt_save = False

    return user, password, prompt_save


def login(session, user, password):
    print("Login in...")

    login_url = "https://www.aulavirtual.urjc.es/moodle/login/index.php"

    login_payload = {
        "anchor": "",
        "logintoken": "",
        "username": user,
        "password": password
    }

    resp = session.post(login_url, data=login_payload)

    # Check if success
    success = resp.headers.get("Expires")
    if not success:
        print("Login failed. Check your user and password and try again")
        exit(1)

    return resp


def prompt_password_save(save, user, password):
    if save:
        save_password = input("Do you want to save your password? (y/N): ").lower() == "y"

        if save_password:
            try:
                keyring.set_password("aula-virtual-dl", user, password)

                print("You password will be stored securely")
            except keyring.errors.PasswordSetError:
                print("Failed to store password")
        else:
            print("You password won't be saved")


def scrape_courses(url, courses):
    soup = BeautifulSoup(url, "html.parser")
    for link in soup.findAll("a"):
        href = link.get("href")
        if href is not None and "/course/view.php" in href:
            courses.add(href)


def download_file(file, stream):
    with open(file, "wb") as out:
        shutil.copyfileobj(stream.raw, out)


def download(args, download_response, file_path, file_name):
    file = os.path.join(file_path, file_name)

    if download_response.status_code == 200:
        if args.overwrite is False:
            size_header = int(download_response.headers.get("Content-Length"))

            if os.path.exists(file):
                if os.path.getsize(file) == size_header:
                    print("\tFile: %s already downloaded" % file_name)

                    return
                else:
                    print("\tFile: %s is outdated. Downloading again" % file_name)
            else:
                print("\tDownloading: " + file_name)

            download_file(file, download_response)

        else:
            print("\tDownloading: " + file_name)

            download_file(file, download_response)


def process_download(link, args, path, session, course_title, not_downloaded):
    if link is not None:
        if "/mod/resource/view.php" in link or "/mod/assign/view.php" in link or "/moodle/mod/folder/view.php" in link:

            # Download file and get filename from response header
            resp = session.get(link, stream=True)

            content_disposition = resp.headers.get("Content-Disposition")

            if content_disposition:
                _, params = cgi.parse_header(content_disposition)

                if exceed_size(args, resp):
                    not_downloaded.append((link, course_title))
                    return

                download(args, resp, path, sanitize_filename(params["filename"].encode("latin-1").decode("utf-8")))

            else:
                linked_files = set()

                resp = session.get(link)
                soup = BeautifulSoup(resp.text, "html.parser")
                title = soup.find("h2").text

                # Check for linked resources or submission files

                links = soup.findAll("a", attrs={"href": re.compile(
                    "/mod_resource/content|/submission_files|/mod_folder/content")})

                for link in links:
                    href = link.get("href")
                    linked_files.add((href, title))

                if len(linked_files) > 0:
                    for resource in linked_files:
                        resp = session.get(resource[0], stream=True)
                        filename = resource[1] + " - " + unquote(
                            os.path.basename(resource[0]).split("?", maxsplit=1)[0])

                        if exceed_size(args, resp):
                            not_downloaded.append((resource[0], course_title))
                            continue

                        download(args, resp, path, sanitize_filename(filename))


def exceed_size(args, response):
    if args.size is not None:
        size = float(args.size)

        # Get file size and convert to MB
        size_header = int(response.headers.get("Content-Length"))
        file_size = size_header / (1024 * 1024)

        if file_size > size:
            return True


def check_course(args, name):
    if args.course is not None:
        if args.course.casefold() in name.casefold():
            return True
    else:
        titles = {"ESCO", "CURF", "RACC"}
        if not any(ele + " -" in name for ele in titles):
            return True


def get_path(args, name):
    if args.route is not None:
        path = os.path.join(args.route, name)
    else:
        path = os.path.join("courses/", name)

    # Create folder where files will be downloaded
    if not os.path.exists(path):
        os.makedirs(path)

    return path


def get_num_workers(args):
    if args.workers is not None:
        num = int(args.workers)
    else:
        num = 5

    return num


def print_header():
    print("###################################################################\n" +
          "# Download all the content from your courses at URJC Aula Virtual #\n" +
          "###################################################################\n")


def print_not_downloaded(file_list):
    if len(file_list) > 0:
        for element in file_list:
            print(element[0], " from ", element[1], " exceeded the maximum download size allowed")


def main():
    args = get_args()

    # Set the browser for the web crawler
    session = setup_browser()

    print_header()

    # Ask for user and password
    user, password, prompt_save = get_credentials(args)

    # Login
    resp = login(session, user, password)

    # Ask for saving password if login succeed
    prompt_password_save(prompt_save, user, password)

    # Inspect home page for courses and save them on a set
    print("\nChecking for courses...")
    courses = set()
    scrape_courses(resp.text, courses)

    files_not_downloaded = []

    # Check every course page
    workers = get_num_workers(args)

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        for course in courses:
            url = session.get(course)
            soup = BeautifulSoup(url.text, "html.parser")
            course_title = soup.find("title").text

            # Don't check unwanted courses
            if check_course(args, course_title):
                course_title = sanitize_filename(course_title)

                print("\nChecking for files in " + course_title)
                path = get_path(args, course_title)

                links = soup.findAll("a", attrs={"href": re.compile("/mod/resource|/mod/assign|/mod/folder")})

                futures = []
                for link in links:
                    href = link.get("href")
                    futures.append(executor.submit(process_download, href, args, path, session, course_title,
                                                   files_not_downloaded))

                concurrent.futures.wait(futures, timeout=None, return_when=concurrent.futures.ALL_COMPLETED)

    print_not_downloaded(files_not_downloaded)


if __name__ == "__main__":
    main()
