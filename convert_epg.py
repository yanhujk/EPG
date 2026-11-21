
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gzip
import re
import urllib.request
import datetime
import xml.etree.ElementTree as ET
import os

SOURCE_URL = "https://epg.pw/xmltv/epg_CN.xml.gz"

OUTPUT_DIR = "_site"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "epg_CN_0800.xml.gz")
TEMP_FILE = OUTPUT_FILE + ".tmp"

# 匹配 start 和 stop 属性中的 +0000
PATTERN = re.compile(
    rb'(start|stop)="(\d{14})\s+\+0000"'
)


def convert_time(match):
    attribute = match.group(1)
    timestamp = match.group(2).decode("ascii")

    dt = datetime.datetime.strptime(
        timestamp, "%Y%m%d%H%M%S"
    )

    # UTC 时间增加 8 小时，改为北京时间
    dt += datetime.timedelta(hours=8)

    new_timestamp = dt.strftime("%Y%m%d%H%M%S")

    return (
        attribute + b'="' +
        new_timestamp.encode("ascii") +
        b' +0800"'
    )


def main():
    print("Downloading:", SOURCE_URL)

    request = urllib.request.Request(
        SOURCE_URL,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept-Encoding": "identity"
        }
    )

    with urllib.request.urlopen(request, timeout=180) as response:
        compressed_data = response.read()

    if not compressed_data:
        raise RuntimeError("Downloaded file is empty")

    print("Downloaded:", len(compressed_data), "bytes")

    # 解压原始 XML.GZ
    try:
        xml_data = gzip.decompress(compressed_data)
    except Exception as e:
        raise RuntimeError("GZIP decompression failed: " + str(e))

    print("XML size:", len(xml_data), "bytes")

    # 统计并转换 start、stop
    matches = PATTERN.findall(xml_data)

    if not matches:
        raise RuntimeError("No +0000 start/stop timestamps found")

    converted_xml = PATTERN.sub(convert_time, xml_data)

    start_count = len(re.findall(
        rb'start="\d{14}\s+\+0800"', converted_xml
    ))

    stop_count = len(re.findall(
        rb'stop="\d{14}\s+\+0800"', converted_xml
    ))

    # 检查 XML 是否有效
    try:
        ET.fromstring(converted_xml)
    except Exception as e:
        raise RuntimeError("XML validation failed: " + str(e))

    # 确保输出目录存在
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 重新压缩，mtime=0 使输出更稳定
    compressed_output = gzip.compress(
        converted_xml,
        compresslevel=9,
        mtime=0
    )

    # 临时文件写入完成后再替换正式文件
    with open(TEMP_FILE, "wb") as f:
        f.write(compressed_output)

    os.replace(TEMP_FILE, OUTPUT_FILE)


# 生成 GitHub Pages 首页
index_html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>EPG 节目表下载</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 700px;
            margin: 60px auto;
            padding: 20px;
            line-height: 1.8;
        }
        .download {
            display: inline-block;
            padding: 12px 24px;
            background: #238636;
            color: white;
            text-decoration: none;
            border-radius: 6px;
        }
    </style>
</head>
<body>
    <h2>EPG 节目表下载</h2>
    <p>数据来源：EPG.PW</p>
    <p>节目时区：北京时间 UTC+8</p>
    <p>更新频率：每天自动更新</p>
    <p>
        <a class="download" href="./epg_CN_0800.xml.gz">
            下载 EPG XML.GZ
        </a>
    </p>
    <p>文件：epg_CN_0800.xml.gz</p>
</body>
</html>
"""

index_path = os.path.join(OUTPUT_DIR, "index.html")

with open(index_path, "w", encoding="utf-8") as f:
    f.write(index_html)

print("Homepage generated:", index_path)

    
    print("--------------------------------")
    print("Conversion successful")
    print("Converted timestamps:", len(matches))
    print("start +0800:", start_count)
    print("stop  +0800:", stop_count)
    print("Output:", OUTPUT_FILE)
    print("Compressed size:", len(compressed_output))
    print("--------------------------------")


if __name__ == "__main__":
    main()
