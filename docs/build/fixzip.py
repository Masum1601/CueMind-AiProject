import sys, zipfile, shutil, os
src = sys.argv[1]; tmp = src + ".tmp"
with zipfile.ZipFile(src) as zi, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zo:
    for it in zi.infolist():
        if it.filename.endswith("/"): continue
        data = zi.read(it.filename)
        comp = zipfile.ZIP_STORED if it.filename.lower().endswith((".mp4", ".jpg", ".png", ".jpeg")) else zipfile.ZIP_DEFLATED
        zo.writestr(it, data, compress_type=comp)
shutil.move(tmp, src); print("clean", os.path.getsize(src) // 1024, "KB")
