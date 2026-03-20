# 座標管理に関して

## WGSとローカル座標

WGS84: maplibreへ渡して地図を描画、GPSを利用する際に対応
ローカル座標: 位置情報特定ロジックに利用

##　ローカル座標

対応する座標をgeojsonに追加？


原点を決定した際の変換をどうするか？

既存案
あらかじめqgisで設定していたすべての座標をそのまま書き出してgeojsonに持たせる

メリット：計算をする必要がない

デメリット：原点を柔軟に決定できない、データ量の倍増


改善案
qgisから情報を取得したうえで、座標を動的計算

AIによると、
次のような情報が揃っていれば実装可能

```
AEQD_local_interact
プロパティ
単位: メートル
動的（プレート固定でないデータに依拠）
天体: Earth
変換法: Azimuthal Equidistant
WKT
PROJCRS["unknown",
    BASEGEOGCRS["unknown",
        DATUM["World Geodetic System 1984",
            ELLIPSOID["WGS 84",6378137,298.257223563,
                LENGTHUNIT["metre",1]],
            ID["EPSG",6326]],
        PRIMEM["Greenwich",0,
            ANGLEUNIT["degree",0.0174532925199433],
            ID["EPSG",8901]]],
    CONVERSION["unknown",
        METHOD["Azimuthal Equidistant",
            ID["EPSG",1125]],
        PARAMETER["Latitude of natural origin",35.4976072,
            ANGLEUNIT["degree",0.0174532925199433],
            ID["EPSG",8801]],
        PARAMETER["Longitude of natural origin",139.6778729,
            ANGLEUNIT["degree",0.0174532925199433],
            ID["EPSG",8802]],
        PARAMETER["False easting",0,
            LENGTHUNIT["metre",1],
            ID["EPSG",8806]],
        PARAMETER["False northing",0,
            LENGTHUNIT["metre",1],
            ID["EPSG",8807]]],
    CS[Cartesian,2],
        AXIS["(E)",east,
            ORDER[1],
            LENGTHUNIT["metre",1,
                ID["EPSG",9001]]],
        AXIS["(N)",north,
            ORDER[2],
            LENGTHUNIT["metre",1,
                ID["EPSG",9001]]]]
Proj4
+proj=aeqd +lat_0=35.4976072 +lon_0=139.6778729 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs
```

```
import proj4 from "proj4";

// 定義
const wgs84 = "EPSG:4326";

const aeqd = `
+proj=aeqd 
+lat_0=35.4976072 
+lon_0=139.6778729 
+x_0=0 
+y_0=0 
+datum=WGS84 
+units=m 
+no_defs
`;

// WGS84 → ローカル
function toLocal(lon, lat) {
  return proj4(wgs84, aeqd, [lon, lat]); // [x, y]
}

// ローカル → WGS84
function toWGS84(x, y) {
  return proj4(aeqd, wgs84, [x, y]); // [lon, lat]
}
```

これらを踏まえて、
1. QGISでローカル座標ベースに、90°かつ正確なマップを描画
2. アプリ側でローカル -> WGS84 / WGS84 -> ローカルへの変換ロジックを実装

スべきこと
1. QGISのデータ整形
2. geojsonとして今まで通りエクスポート
3. アプリ側で変換ロジックの実装

studyhall / interact 用で分割



QGISの内容再確認
exports/rawへの出力方法　手動か自動か
buildロジック（exportsを整形、情報追加して、buildへ）
buildを対象にgithubへプッシュできるか確認

座標変換ロジックの実装？

ローディングロジックの実装