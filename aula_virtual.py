#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2018 Aitor Alonso at aalonso@aalonso.eu
# Copyright (C) 2020 Jorge Portal
# This script is under MIT license
#
# Version: 2020.03.27
# You can find new versions and fixes of this script over the time at
# https://github.com/jprtal/aula-virtual-dl

import http.cookiejar as cookielib
from bs4 import BeautifulSoup as bs
import cgi
import mechanize
import os
import getpass
import argparse
from urllib.parse import unquote
from pathvalidate import sanitize_filename
import keyring
import re


def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("-r", "--route", help="location to download")
    parser.add_argument("-u", "--user", help="user")
    parser.add_argument("-s", "--size", help="maximum file size in MB")
    parser.add_argument("-c", "--course", help="course name")
    parser.add_argument("-o", "--overwrite", action='store_true', help="overwrite existing files")

    return parser.parse_args()


def setup_browser():
    br = mechanize.Browser()
    cookiejar = cookielib.LWPCookieJar()
    br.set_cookiejar(cookiejar)

    br.set_handle_equiv(True)
    br.set_handle_gzip(True)
    br.set_handle_redirect(True)
    br.set_handle_referer(True)
    br.set_handle_robots(False)

    br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)
    br.addheaders = [('User-agent',
                      'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.70 Safari/537.36')]

    return br


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


def login(browser, url, user, password):
    # Submit login form
    print("Login in...")

    browser.select_form(nr=0)
    browser.form['username'] = user
    browser.form['password'] = password
    browser.submit(id="loginbtn")

    # Check if success
    url = browser.open(url)
    success = url.get('Expires', None)
    if not success:
        print("Login failed. Check your user and password and try again")
        exit(1)

    return url


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
    soup = bs(url, "html.parser")
    for link in soup.findAll("a"):
        href = link.get("href")
        if href is not None and "/course/view.php" in href:
            courses.add(href)


def download_file(file, stream):
    fh = open(file, 'wb')
    fh.write(stream.read())
    fh.close()


def download(args, download_response, file_path, file_name):
    file = os.path.join(file_path, file_name)

    if args.overwrite is False:
        size_header = int(download_response.get('Content-Length', None))

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


def process_download(link, args, path, browser, course_title, not_downloaded):
    if link is not None:
        if "/mod/resource/view.php" in link or "/mod/assign/view.php" in link:

            # Download file and get filename from response header
            response = browser.open(link)
            cdheader = response.get('Content-Disposition', None)
            if cdheader is not None:
                value, params = cgi.parse_header(cdheader)

                if exceed_size(args, response):
                    not_downloaded.append((link, course_title))
                    return

                download(args, response, path, sanitize_filename(params["filename"].encode("latin-1").decode("utf-8")))
            else:
                linked_files = set()

                url = browser.open(link)
                soup = bs(url, "html.parser")
                title = soup.find("h2").text

                # Check for linked resources or submission files
                for link in soup.findAll("a"):
                    link = link.get("link")
                    if link is not None:
                        if "/mod_resource/content" in link or "/submission_files" in link:
                            linked_files.add((link, title))

                for resource in linked_files:
                    response = browser.open(resource[0])
                    filename = resource[1] + " - " + unquote(
                        os.path.basename(resource[0]).split('?', maxsplit=1)[0])

                    if exceed_size(args, response):
                        not_downloaded.append((resource[0], course_title))
                        continue

                    download(args, response, path, sanitize_filename(filename))


def exceed_size(args, size_response):
    if args.size is not None:
        size = float(args.size)

        # Get file size and convert to MB
        size_header = int(size_response.get('Content-Length', None))
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

    BASE_URL = "https://www.aulavirtual.urjc.es/moodle/"

    # Set the browser for the web crawler
    br = setup_browser()
    br.open(BASE_URL)

    print_header()

    # Ask for user and password
    user, password, prompt_save = get_credentials(args)

    # Login
    url = login(br, BASE_URL, user, password)

    # Ask for saving password if login succeed
    prompt_password_save(prompt_save, user, password)

    # Inspect home page for courses and save them on a set
    print("\nChecking for courses...")
    courses = set()
    scrape_courses(url, courses)

    files_not_downloaded = []

    # Check every course page
    for course in courses:
        url = br.open(course)
        soup = bs(url, "html.parser")
        course_title = soup.find("title").text

        # Don't check unwanted courses
        if check_course(args, course_title):
            course_title = sanitize_filename(course_title)

            print("\nChecking for files in " + course_title)
            path = get_path(args, course_title)

            links = soup.findAll("a", attrs={'href': re.compile("/mod/resource|/mod/assign")})

            for link in links:
                href = link.get("href")
                process_download(href, args, path, br, course_title, files_not_downloaded)

    print_not_downloaded(files_not_downloaded)


if __name__ == "__main__":
    main()
