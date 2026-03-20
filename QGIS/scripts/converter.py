#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
convert_imdf_batch_ordered_with_centroid.py

説明:
 - フォルダ内の .geojson を一括変換（以前と同じ変換ルール）
 - 出力 Feature のキー順を厳密に制御:
     (id) -> "type": "Feature" -> feature_type -> geometry -> properties
 - geometry の座標群からポリゴン重心を算出して
   properties.display_point.coordinates に格納する機能を追加
 - CONFIG を編集して使用
"""
from copy import deepcopy
from pathlib import Path
import json, shutil, sys, math

# ------------------ 設定（ここを編集） ------------------
CONFIG = {
    "input_folder": "../working/local_map - studyhall/exports/footprint/input",
    "output_folder": "../working/local_map - studyhall/exports/footprint/output",
    "recursive": True,
    "backup_existing": True,
    "verbose": True,
    "extensions": [".geojson", ".GeoJSON"]
}
# ------------------ 設定ここまで ------------------

# ---------- ジオメトリ変換ユーティリティ ----------

def convert_geometry(geom):
    """MultiPolygon (要素1) -> Polygon に変換。それ以外はそのまま返す"""
    if not geom:
        return geom
    g = deepcopy(geom)
    t = g.get("type")
    coords = g.get("coordinates")
    if t == "MultiPolygon" and isinstance(coords, list) and len(coords) == 1:
        return {"type": "Polygon", "coordinates": coords[0]}
    return g

# ---------- ポリゴン重心計算ユーティリティ ----------

def _ring_signed_area_and_centroid_sum(ring):
    """
    linear ring: list of [x,y] with first != last ideally (if closed, last==first)
    return tuple (cross_sum, numx_sum, numy_sum)
    where cross_sum = sum(xi*yi1 - xi1*yi)
    and numx_sum = sum((xi + xi1) * cross_i)
          numy_sum = sum((yi + yi1) * cross_i)
    """
    if not ring or len(ring) < 3:
        return 0.0, 0.0, 0.0
    xs = ring
    n = len(xs)
    cross_sum = 0.0
    numx_sum = 0.0
    numy_sum = 0.0
    for i in range(n):
        x0, y0 = xs[i]
        x1, y1 = xs[(i + 1) % n]
        cross = x0 * y1 - x1 * y0
        cross_sum += cross
        numx_sum += (x0 + x1) * cross
        numy_sum += (y0 + y1) * cross
    return cross_sum, numx_sum, numy_sum

def compute_centroid_from_polygon_rings(rings):
    """
    rings: list of linear rings for a polygon (rings[0] = outer, subsequent = holes)
    returns (cx, cy, area) where area is signed area/2 sum across rings

    数値安定化のため、計算前に座標を局所座標系に平行移動してから計算します。
    これにより、緯度経度のような大きな絶対値を持つ座標での打ち消し誤差を防ぎます。
    """
    if not rings or not rings[0]:
        return None

    # 参照点: 外側輪郭の最初の頂点（閉じている場合はその最初の点）
    try:
        refx, refy = rings[0][0]
    except Exception:
        return None

    total_cross = 0.0
    total_numx = 0.0
    total_numy = 0.0

    for ring in rings:
        # build shifted ring (local coordinates)
        shifted = []
        for p in ring:
            if not (isinstance(p, (list, tuple)) and len(p) >= 2):
                continue
            shifted.append((float(p[0]) - refx, float(p[1]) - refy))

        if len(shifted) < 3:
            continue

        n = len(shifted)
        for i in range(n):
            x0, y0 = shifted[i]
            x1, y1 = shifted[(i + 1) % n]
            cross = x0 * y1 - x1 * y0
            total_cross += cross
            total_numx += (x0 + x1) * cross
            total_numy += (y0 + y1) * cross

    area = total_cross / 2.0
    # area が非常に小さい（ほぼゼロ）なら退避
    if abs(area) < 1e-12:
        return None  # degenerate

    # ローカル座標での重心
    cx_local = total_numx / (6.0 * area)
    cy_local = total_numy / (6.0 * area)

    # 元の座標系へ戻す
    cx = cx_local + refx
    cy = cy_local + refy
    return (cx, cy, area)

def compute_centroid_from_geometry(geom):
    """
    geom: GeoJSON geometry dict (Polygon or MultiPolygon)
    returns [cx, cy] or None if cannot compute
    """
    if not geom or "type" not in geom:
        return None
    t = geom.get("type")
    if t == "Polygon":
        # geom["coordinates"]: [ ring0, ring1, ... ]
        res = compute_centroid_from_polygon_rings(geom.get("coordinates", []))
        if res is not None:
            cx, cy, area = res
            return [cx, cy]
        # fallback to average of outer ring vertices
        outer = geom.get("coordinates", [])
        if outer and len(outer) > 0:
            ring = outer[0]
            return average_point(ring)
        return None
    elif t == "MultiPolygon":
        # MultiPolygon: [ polygon0, polygon1, ... ] where polygon = [ring0, ring1, ...]
        total_area = 0.0
        weighted_x = 0.0
        weighted_y = 0.0
        polys = geom.get("coordinates", [])
        for poly in polys:
            res = compute_centroid_from_polygon_rings(poly)
            if res is None:
                # degenerate polygon: try fallback average of outer ring
                if poly and len(poly) > 0 and poly[0] and len(poly[0]) > 0:
                    avg = average_point(poly[0])
                    if avg:
                        # approximate very small area to include it minimally
                        weighted_x += avg[0] * 1e-9
                        weighted_y += avg[1] * 1e-9
                        total_area += 1e-9
                continue
            cx, cy, area = res
            weighted_x += cx * area
            weighted_y += cy * area
            total_area += area
        if abs(total_area) < 1e-12:
            # fallback: average of first polygon outer ring
            if polys and len(polys) > 0 and polys[0] and len(polys[0]) > 0:
                return average_point(polys[0][0])
            return None
        return [weighted_x / total_area, weighted_y / total_area]
    else:
        return None

def average_point(points):
    """単純平均（fallback用）"""
    if not points:
        return None
    sx = 0.0
    sy = 0.0
    n = 0
    for p in points:
        if not (isinstance(p, (list, tuple)) and len(p) >= 2):
            continue
        sx += float(p[0])
        sy += float(p[1])
        n += 1
    if n == 0:
        return None
    return [sx / n, sy / n]

# ---------- 表示関連ユーティリティ（前バージョンと互換） ----------

def normalize_display_point(val):
    """display_point を標準オブジェクトに正規化"""
    if val is None:
        return {"type": "Point", "coordinates": []}
    if isinstance(val, dict) and val.get("type") == "Point" and "coordinates" in val:
        return val
    if isinstance(val, list):
        return {"type": "Point", "coordinates": val}
    return {"type": "Point", "coordinates": []}

def extract_name_object(props):
    ja = None
    en = None
    if not props:
        return {"ja": None, "en": None}
    if "name_ja" in props and props.get("name_ja") is not None:
        ja = props.get("name_ja")
    if "name_en" in props and props.get("name_en") is not None:
        en = props.get("name_en")
    name_field = props.get("name")
    if (ja is None or en is None) and name_field is not None:
        if isinstance(name_field, dict):
            if ja is None and "ja" in name_field:
                ja = name_field.get("ja")
            if en is None and "en" in name_field:
                en = name_field.get("en")
            if ja is None and "ja-JP" in name_field:
                ja = name_field.get("ja-JP")
            if en is None and "en-US" in name_field:
                en = name_field.get("en-US")
        elif isinstance(name_field, str):
            if en is None:
                en = name_field
    return {"ja": ja, "en": en}

def convert_properties(props):
    p = {} if props is None else deepcopy(props)
    out = {}
    out["category"] = p.get("category") or p.get("cat") or None
    out["restriction"] = p.get("restricte") if "restricte" in p else p.get("restriction")
    out["accessibility"] = p.get("access") if "access" in p else p.get("accessibility")
    out["name"] = extract_name_object(p)
    out["alt_name"] = p.get("alt_name") if "alt_name" in p else p.get("altname") if "altname" in p else None
    # display_point は後で重心で上書きするため一旦 normalize（存在しない場合は空point）
    dp = None
    if "display_po" in p:
        dp = p.get("display_po")
    elif "display_point" in p:
        dp = p.get("display_point")
    out["display_point"] = normalize_display_point(dp)

    # --- level_id: 入力値を優先してそのまま反映する設計に変更 ---
    # 優先順: p["level_id"] -> p["level"]
    # ただし値が None または空文字列の場合は無視して None にする
    lvl = None
    if isinstance(p, dict):
        raw_lvl_id = p.get("level_id", None) if "level_id" in p else None
        raw_level = p.get("level", None) if "level" in p else None

        # 有効な文字列があればそれを採用（数値や他型でも str にして採用したい場合は adjust 可能）
        if raw_lvl_id is not None and str(raw_lvl_id).strip() != "":
            lvl = raw_lvl_id
        elif raw_level is not None and str(raw_level).strip() != "":
            lvl = raw_level
        else:
            lvl = None

    out["level_id"] = lvl

    return out

# ---------- Feature を指定順で組み立て、centroid を properties.display_point に入れる ----------

def build_ordered_feature(orig_feature):
    """
    orig_feature: 元の Feature dict（任意のキー構成）
    戻り値: 指定の順序で組み直した新しい Feature dict
    順序: (id) -> "type":"Feature" -> feature_type -> geometry -> properties
    """
    f = deepcopy(orig_feature)
    props = f.get("properties") or {}

    # 1) compute values to place
    top_id = props.get("id") or f.get("id")
    feature_type_val = props.get("feature_t") or props.get("feature_type") or f.get("feature_type")
    geom = convert_geometry(f.get("geometry"))
    new_props = convert_properties(props)

    # compute centroid from geometry and set display_point.coordinates
    centroid = compute_centroid_from_geometry(geom) if geom is not None else None
    if centroid:
        # 小数点は必要なら丸め（ここではそのまま）
        new_props["display_point"] = {"type": "Point", "coordinates": [centroid[0], centroid[1]]}
    else:
        # 既定の normalize 値のまま（空配列）
        new_props["display_point"] = normalize_display_point(new_props.get("display_point"))

    # remove meta keys from properties if present to avoid duplication
    for k in ("id", "feature_t", "feature_type", "restricte", "access", "display_po", "name_ja", "name_en"):
        if k in new_props:
            new_props.pop(k, None)

    # 2) create ordered dict by insertion order
    ordered = {}

    # id があれば先頭に入れる（ユーザー指定通り "type" の直前）
    if top_id is not None:
        ordered["id"] = top_id

    # 次に type は必ず "Feature"
    ordered["type"] = "Feature"

    # feature_type を type の直後に置く（存在する場合）
    if feature_type_val is not None:
        ordered["feature_type"] = feature_type_val

    # geometry を properties より先に置く
    ordered["geometry"] = geom if geom is not None else None

    # 最後に properties
    ordered["properties"] = new_props

    return ordered

# ---------- GeoJSON 全体処理 ----------

def process_geojson(root):
    if not isinstance(root, dict):
        raise ValueError("GeoJSON root must be a JSON object")
    t = root.get("type")
    if t == "FeatureCollection":
        features = root.get("features", [])
        new_feats = []
        for feat in features:
            try:
                new_feats.append(build_ordered_feature(feat))
            except Exception as e:
                print(f"[Warning] Converting a feature failed: {e}", file=sys.stderr)
        out_root = {}
        for k, v in root.items():
            if k == "features":
                continue
            out_root[k] = deepcopy(v)
        out_root["type"] = "FeatureCollection"
        out_root["features"] = new_feats
        return out_root
    elif t == "Feature":
        return build_ordered_feature(root)
    else:
        raise ValueError(f"Unsupported GeoJSON root type: {t}")

# ---------- バッチ処理ロジック（以前と同じ） ----------

def find_geojson_files(input_dir: Path, extensions, recursive: bool = True):
    files = []
    if recursive:
        for ext in extensions:
            files.extend(list(input_dir.rglob(f"*{ext}")))
    else:
        for ext in extensions:
            files.extend(list(input_dir.glob(f"*{ext}")))
    unique = sorted(set(files))
    return unique

def process_file(input_path: Path, output_path: Path, cfg):
    try:
        with input_path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception as e:
        print(f"[Error] Failed to read JSON from {input_path}: {e}", file=sys.stderr)
        return False

    try:
        converted = process_geojson(data)
    except Exception as e:
        print(f"[Error] Failed to convert {input_path}: {e}", file=sys.stderr)
        return False

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.exists() and cfg.get("backup_existing"):
            bak = output_path.with_suffix(output_path.suffix + ".bak")
            try:
                shutil.move(str(output_path), str(bak))
            except Exception as e:
                print(f"[Warning] Failed to backup existing file {output_path}: {e}", file=sys.stderr)
        with output_path.open("w", encoding="utf-8") as fh:
            json.dump(converted, fh, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Error] Failed to write output to {output_path}: {e}", file=sys.stderr)
        return False

    return True

def run_batch(cfg):
    in_dir = Path(cfg.get("input_folder"))
    out_dir = Path(cfg.get("output_folder"))
    recursive = bool(cfg.get("recursive", True))
    exts = cfg.get("extensions", [".geojson", ".GeoJSON"])
    verbose = bool(cfg.get("verbose", True))

    if not in_dir.exists() or not in_dir.is_dir():
        print(f"[Error] input_folder does not exist or is not a directory: {in_dir}", file=sys.stderr)
        return

    out_dir.mkdir(parents=True, exist_ok=True)

    files = find_geojson_files(in_dir, exts, recursive=recursive)
    if not files:
        print("[Info] No .geojson files found in input folder.", file=sys.stderr)
        return

    success_count = 0
    fail_count = 0

    for fpath in files:
        try:
            rel = fpath.relative_to(in_dir)
        except Exception:
            rel = fpath.name
        out_path = out_dir.joinpath(rel)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if verbose:
            print(f"[Info] Converting: {fpath} -> {out_path}")

        ok = process_file(fpath, out_path, cfg)
        if ok:
            success_count += 1
        else:
            fail_count += 1

    print(f"[Done] Converted: {success_count}, Failed: {fail_count}")

def main():
    try:
        run_batch(CONFIG)
    except Exception as e:
        print(f"[Fatal] Unexpected error: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
