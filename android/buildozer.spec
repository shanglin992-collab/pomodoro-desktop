[app]

# (str) Title of your application
title = 番茄钟

# (str) Package name
package.name = pomodoro

# (str) Package domain (needed for android/ios packaging)
package.domain = org.pomodoro

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,ico,json

# (list) List of inclusions using pattern matching
#source.include_patterns = assets/*,images/*.png

# (str) Application versioning (method 1)
version = 1.0

# (str) Application versioning (method 2)
# version.regex = __version__ = ['"](.*)['"]

# (str) Master Link, this is the only url involved in kivy link
# used to detect if it's a new version or not
# default = https://github.com/kivy/kivy/archive/master.zip

# (str) Kivy version to use (leave empty for latest)
# kivy = 2.3.0

# (str) Application icon
icon.filename = assets/icon.png

# (list) Supported orientations
orientation = portrait

# (list) List of service to declare
#services = Name:Path

# (bool) Indicate if the application is fullscreen or not
fullscreen = 0

# (bool) Show the status bar
# In Kivy, fullscreen=0 leaves room for the status bar; set 1 to hide it.
statusbar = 1

#
# Python for android (p4a) specific
#

# (str) Supported python version
android.python_version = 3.11

# (list) List of Android permissions
android.permissions = VIBRATE

# (int) Target Android API level
android.api = 34

# (int) Minimum API level
android.minapi = 24

# (bool) Android adaptive icon (recommended)
android.adaptive_icon_background = "#1e1e2e"
android.adaptive_icon_foreground = assets/icon.png

# (bool) Show build log
log_level = 2

# (str) Path to the directory containing the buildozer.spec
# build_dir = ./build

[buildozer]

# (int) Log level
log_level = 2

# (str) Path to build artifact storage
# buildozer.binaries_directory = ./bin

# (str) Path to the directory where buildozer keeps its state
# .buildozer is default

# (list) App dependencies
requirements = python3,kivy==2.3.0,plyer==2.1.1

# (bool) Use the AndroidX support library
android.enable_androidx = True

# (str) Android NDK version
# android.ndk = 25b

# (bool) Android logcat filters
# android.logcat_filters = *:S python:D

# (bool) Android arch
android.archs = arm64-v8a

[app:android]
# (bool) Indicate if the application should be installable from the Play Store
android.is.private.storage = False
