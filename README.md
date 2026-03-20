# Hello Dev!!

## Description 
This project make to support "FrontierAtlas".

Serve the GeoJson data.

## how to use??

### dev

#### QGIS -> exports

open the QGIS app and run the script **allExports1.py**

#### exports -> build

run the script **transform.js**

#### build -> github 

first settings
1. set the tag in bash

   ```
   git tag v0.0.0
   ```

2. push them

   ```
   git push origin v0.0.0
   ```

3. then CI systems run and build the files & sites

reset tag 

1. delete local tag
   ```
   git tag -d v0.0.0
   ```

2. delete online tag
   ```
   git push origin --delete v0.0.0
   ```

3. then you can remake the new tag

### user