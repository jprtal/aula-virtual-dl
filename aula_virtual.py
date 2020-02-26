#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2018 Aitor Alonso at aalonso@aalonso.eu
# Copyright (C) 2020 Jorge Portal
# This script is under MIT license
#
# Version: 2019.02.22
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


def download_file(download_response, file_path, file_name):
    file = os.path.join(file_path, file_name)
    print("\tDownloading: " + file_name)

    fh = open(file, 'wb')
    fh.write(download_response.read())
    fh.close()


def exceed_size(size_response):
    if args.size is not None:
        size = float(args.size)

        # Get file size and convert to MB
        size_header = int(size_response.get('Content-Length', None))
        file_size = size_header / (1024 * 1024)

        if file_size > size:
            return True


def check_course(name):
    if args.course is not None:
        if args.course.casefold() in name.casefold():
            return True
    else:
        if not "ESCO" in course_title and not "CURF" in course_title:
            return True


parser = argparse.ArgumentParser()

parser.add_argument("-r", "--route", help="location to download")
parser.add_argument("-u", "--user", help="user")
parser.add_argument("-s", "--size", help="maximum file size in MB")
parser.add_argument("-c", "--course", help="course name")

args = parser.parse_args()

BASE_URL = "https://www.aulavirtual.urjc.es/moodle/"

# Set the browser for the web crawler
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
br.open(BASE_URL)

# Ask for user and password
print("###################################################################\n" +
      "# Download all the content from your courses at URJC Aula Virtual #\n" +
      "###################################################################\n")

if args.user is not None:
    user = args.user
else:
    user = input("Enter user: ")
passwd = getpass.getpass(prompt="Enter password: ")

# Submit login form
print("Login in...")
br.select_form(nr=0)
br.form['username'] = user
br.form['password'] = passwd
br.submit(id="loginbtn")

# Check if success
url = br.open(BASE_URL)
login = url.get('Expires', None)
if not login:
    print("Login failed. Check your user and password and try again")
    exit(1)

# Inspect home page for courses and save them on a set
print("Checking for courses...")
courses = set()
linked_files = set()

soup = bs(url, "html.parser")
for link in soup.findAll("a"):
    href = link.get("href")
    if href is not None and "/course/view.php" in href:
        courses.add(href)

not_downloaded_size = []

# Check every course page
for course in courses:
    url = br.open(course)
    soup = bs(url, "html.parser")
    course_title = soup.find("title").text

    # Don't check unwanted courses
    if check_course(course_title):

        # Create folder where files will be downloaded
        if args.route is not None:
            path = os.path.join(args.route, course_title.replace("/", "."))
        else:
            path = os.path.join("courses/", course_title.replace("/", "."))

        print("\nChecking for files in " + course_title)

        if not os.path.exists(path):
            os.makedirs(path)

        # Check for files to download
        for link in soup.findAll("a"):
            href = link.get("href")
            if href is not None and "/mod/resource/view.php" in href:

                # Download file and get filename from response header
                response = br.open(href)
                cdheader = response.get('Content-Disposition', None)
                if cdheader is not None:
                    value, params = cgi.parse_header(cdheader)

                    if exceed_size(response):
                        not_downloaded_size.append((href, course_title))
                        continue
                else:
                    url = br.open(href)
                    soup = bs(url, "html.parser")

                    # Check for linked resources
                    for link in soup.findAll("a"):
                        href = link.get("href")
                        if href is not None and "/mod_resource/content" in href:
                            linked_files.add(href)

                    for resource in linked_files:
                        response = br.open(resource)
                        filename = unquote(os.path.basename(resource))

                        if exceed_size(response):
                            not_downloaded_size.append((resource, course_title))
                            continue

                        download_file(response, path, filename)

                    linked_files.clear()
                    continue

                download_file(response, path, params["filename"].encode("latin-1").decode("utf-8"))

if len(not_downloaded_size) > 0:
    for element in not_downloaded_size:
        print(element[0], " from ", element[1], " exceeded the maximum download size allowed")
