import os

# Delete the cached Python bytecode of the apps
os.system("rm -rf stats/__pycache__/")
os.system("rm -rf courses/__pycache__/")
os.system("rm -rf feedback/__pycache__/")
os.system("rm -rf exercise_admin/__pycache__/")
os.system("rm -rf lovelace/__pycache__/")

# Delete the cached Python bytecode of the templatetags
os.system("rm -rf stats/templatetags/__pycache__/")
os.system("rm -rf courses/templatetags/__pycache__/")
os.system("rm -rf exercise_admin/templatetags/__pycache__/")

# Delete the cached Python bytecode of migrations
os.system("rm -rf courses/migrations/__pycache__/")
os.system("rm -rf feedback/migrations/__pycache__/")

# Delete the migrations
os.system("rm -rf courses/migrations/0*")
os.system("rm -rf feedback/migrations/0*")
