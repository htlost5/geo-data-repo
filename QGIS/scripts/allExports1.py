import os
import shutil
from osgeo import ogr
from qgis.core import (
    QgsVectorLayer,
    QgsVectorFileWriter,
    QgsCoordinateReferenceSystem,
    QgsProject,
)

# -----------------------------
# 設定
# -----------------------------
INPUT_ROOT = r"D:\htlost5_projects\geo-data-repo\QGIS\working"
OUTPUT_ROOT = r"D:\htlost5_projects\geo-data-repo\exports\raw"

TARGET_CRS = QgsCoordinateReferenceSystem("EPSG:4326")
TRANSFORM_CONTEXT = QgsProject.instance().transformContext()

TARGET_ROOTS = {"studyhall", "interact"}


# -----------------------------
# 初期化（完全削除）
# -----------------------------
def reset_output_dir():
    print(f"[RESET] Removing directory: {OUTPUT_ROOT}")
    shutil.rmtree(OUTPUT_ROOT, ignore_errors=True)
    print(f"[RESET] Removed: {OUTPUT_ROOT}")
    os.makedirs(OUTPUT_ROOT, exist_ok=True)
    print(f"[RESET] Recreated: {OUTPUT_ROOT}")


# -----------------------------
# 書き込み
# -----------------------------
def safe_write(vlayer, output_path):
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "GeoJSON"
    options.fileEncoding = "UTF-8"
    options.destCRS = TARGET_CRS

    res = QgsVectorFileWriter.writeAsVectorFormatV3(
        vlayer,
        output_path,
        TRANSFORM_CONTEXT,
        options,
    )
    return res[0]


# -----------------------------
# GPKG → GeoJSON
# -----------------------------
def convert_gpkg_to_geojson(gpkg_path, output_path):
    print(f"[EXPORT] Source: {gpkg_path}")

    ds = ogr.Open(gpkg_path)
    if ds is None:
        print(f"[ERROR] Failed to open: {gpkg_path}")
        return

    layer_count = ds.GetLayerCount()
    print(f"[EXPORT] Layer count: {layer_count}")

    for i in range(layer_count):
        layer = ds.GetLayerByIndex(i)
        layer_name = layer.GetName()

        uri = f"{gpkg_path}|layername={layer_name}"
        vlayer = QgsVectorLayer(uri, layer_name, "ogr")

        if not vlayer.isValid():
            print(f"[ERROR] Invalid layer: {gpkg_path} / {layer_name}")
            continue

        final_output_path = output_path
        if layer_count > 1:
            base, ext = os.path.splitext(output_path)
            final_output_path = f"{base}_{layer_name}{ext}"

        os.makedirs(os.path.dirname(final_output_path), exist_ok=True)

        print(f"[EXPORT] Writing: {final_output_path}")
        result = safe_write(vlayer, final_output_path)

        if result != QgsVectorFileWriter.NoError:
            print(f"[ERROR] Export failed: {final_output_path}")
        else:
            print(f"[OK] Export completed: {final_output_path}")


# -----------------------------
# パス変換
# -----------------------------
def map_output_path(input_path):
    rel = os.path.relpath(input_path, INPUT_ROOT)
    parts = rel.split(os.sep)

    if not parts:
        return None

    # 先頭ファイル名の拡張子を除いた名前
    top_name = os.path.splitext(parts[0])[0]
    filename = os.path.splitext(parts[-1])[0] + ".geojson"

    # overview_map.gpkg -> raw 直下
    if len(parts) == 1 and top_name == "overview_map":
        return os.path.join(OUTPUT_ROOT, filename)

    # studyhall / interact 配下
    if parts[0] in TARGET_ROOTS:
        root = parts[0]

        # studyhall/footprint.gpkg, studyhall/stairs.gpkg, interact/footprint.gpkg など
        if len(parts) == 2:
            if parts[1].lower() in {"footprint.gpkg", "stairs.gpkg"}:
                return os.path.join(OUTPUT_ROOT, root, filename)

        # studyhall/floors/floor1/units.gpkg
        if len(parts) == 4 and parts[1] == "floors":
            return os.path.join(
                OUTPUT_ROOT,
                root,
                "floors",
                parts[2],
                filename
            )

        # studyhall/levels/floor1-3.gpkg
        if len(parts) == 3 and parts[1] == "levels":
            return os.path.join(
                OUTPUT_ROOT,
                root,
                "levels",
                filename
            )

    return None


# -----------------------------
# 実行
# -----------------------------
def main():
    print("[START] Export process begins")
    reset_output_dir()

    for root, _, files in os.walk(INPUT_ROOT):
        for file in files:
            if file.lower().endswith(".gpkg"):
                input_path = os.path.join(root, file)
                output_path = map_output_path(input_path)

                if output_path is None:
                    print(f"[SKIP] {input_path}")
                    continue

                convert_gpkg_to_geojson(input_path, output_path)

    print("[DONE] All exports finished ✅")


main()