
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

PATTERN = re.compile(
    rb'(start|stop)="(\d{14})\s+\+0000"'
)


def convert_time(match):
    attribute = match.group(1)
    timestamp = match.group(2).decode("ascii")

    dt = datetime.datetime.strptime(
        timestamp, "%Y%m%d%H%M%S"
    )

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
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urllib.request.urlopen(request, timeout=180) as response:
        compressed_data = response.read()

    if not compressed_data:
        raise RuntimeError("Downloaded file is empty")

    print("Downloaded:", len(compressed_data), "bytes")

    # 解压 XML.GZ
    xml_data = gzip.decompress(compressed_data)

    print("XML size:", len(xml_data), "bytes")

    # 统计原始时间
    start_count = len(re.findall(
        rb'start="\d{14}\s+\+0000"', xml_data
    ))

    stop_count = len(re.findall(
        rb'stop="\d{14}\s+\+0000"', xml_data
    ))

    total_count = start_count + stop_count

    if total_count == 0:
        raise RuntimeError("No +0000 timestamps found")

    # 转换所有 start 和 stop
    converted_xml = PATTERN.sub(convert_time, xml_data)

    # 检查 XML 格式
    ET.fromstring(converted_xml)

    # 检查转换结果
    remaining = len(re.findall(
        rb'(start|stop)="\d{14}\s+\+0000"',
        converted_xml
    ))

    if remaining != 0:
        raise RuntimeError("Some +0000 timestamps remain")

    # 创建输出目录
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 重新压缩
    compressed_output = gzip.compress(
        converted_xml,
        compresslevel=9,
        mtime=0
    )

    with open(TEMP_FILE, "wb") as f:
        f.write(compressed_output)

    os.replace(TEMP_FILE, OUTPUT_FILE)

    # 生成首页
    index_html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>EPG 节目表下载</title>
</head>
<body>
<h2>EPG 节目表下载</h2>
<p>数据来源：EPG.PW</p>
<p>节目时区：北京时间 UTC+8</p>
<p>更新频率：每天自动更新</p>
<p>
<a href="./epg_CN_0800.xml.gz">
下载 EPG XML.GZ
</a>
</p>
</body>
</html>
"""

    index_path = os.path.join(OUTPUT_DIR, "index.html")

    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_html)

    # 输出执行结果
    print("--------------------------------")
    print("Conversion successful")
    print("Original start +0000:", start_count)
    print("Original stop +0000:", stop_count)
    print("Total converted:", total_count)
    print("Remaining +0000:", remaining)
    print("Output:", OUTPUT_FILE)
    print("Homepage:", index_path)
    print("--------------------------------")


if __name__ == "__main__":
    main()
