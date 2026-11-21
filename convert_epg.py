
import gzip
import re
import os
import urllib.request
import xml.etree.ElementTree as ET

SOURCE_URL = "https://epg.pw/xmltv/epg_CN.xml.gz"

OUTPUT_DIR = "_site"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "epg_CN_0800.xml.gz")
INDEX_FILE = os.path.join(OUTPUT_DIR, "index.html")


def download_source():
    print("Downloading:", SOURCE_URL)

    request = urllib.request.Request(
        SOURCE_URL,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def convert_xml(xml_data):
    # 1. 仅修改 programme 的 start / stop 时区标记。
    #    保留原来的14位时间数字，不进行任何时间加减。
    time_pattern = re.compile(
        rb'(start|stop)="(\d{14})\s+\+0000"'
    )

    xml_data, time_count = time_pattern.subn(
        lambda m: m.group(1) + b'="' + m.group(2) + b' +0800"',
        xml_data
    )

    # 2. 删除根节点 <tv> 的 date 属性。
    tv_pattern = re.compile(rb'<tv\b[^>]*>')

    tv_match = tv_pattern.search(xml_data)
    tv_date_count = 0

    if tv_match:
        tv_tag = tv_match.group(0)

        tv_tag, tv_date_count = re.subn(
            rb'\s+date\s*=\s*("[^"]*"|\'[^\']*\')',
            b'',
            tv_tag,
            count=1
        )

        xml_data = (
            xml_data[:tv_match.start()]
            + tv_tag
            + xml_data[tv_match.end():]
        )
    else:
        raise RuntimeError("Cannot find XML root <tv>")

    # 3. 删除 programme 节点中的 desc、date、audio 子节点。
    remove_tag_pattern = re.compile(
        rb'<(desc|date|audio)\b[^>]*/\s*>'
        rb'|'
        rb'<(desc|date|audio)\b[^>]*>.*?</\2\s*>',
        re.DOTALL
    )

    # 使用逐个 programme 处理的方式，避免误删 programme 外部内容。
    programme_pattern = re.compile(
        rb'(<programme\b[^>]*>)(.*?)(</programme\s*>)',
        re.DOTALL
    )

    removed = {
        "desc": 0,
        "date": 0,
        "audio": 0
    }

    def clean_programme(match):
        opening = match.group(1)
        body = match.group(2)
        closing = match.group(3)

        def remove_element(element_match):
            tag = element_match.group(1) or element_match.group(2)

            if tag:
                tag_name = tag.decode("ascii")
                removed[tag_name] += 1

            return b''

        body = remove_tag_pattern.sub(remove_element, body)

        return opening + body + closing

    xml_data, programme_count = programme_pattern.subn(
        clean_programme,
        xml_data
    )

    return xml_data, {
        "time_replacements": time_count,
        "tv_date_removed": tv_date_count,
        "programme_count": programme_count,
        "desc_removed": removed["desc"],
        "date_removed": removed["date"],
        "audio_removed": removed["audio"]
    }


def validate_xml(xml_data):
    # 检查转换后的 XML 是否仍然有效。
    ET.fromstring(xml_data)
    print("XML validation: OK")


def write_gzip_file(xml_data):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 使用固定 mtime，避免每次生成的 gzip 时间戳不同。
    with open(OUTPUT_FILE, "wb") as output:
        with gzip.GzipFile(
            fileobj=output,
            mode="wb",
            filename="",
            mtime=0
        ) as gz:
            gz.write(xml_data)

    print("Output:", OUTPUT_FILE)


def write_index():
    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>EPG XMLTV 下载</title>
</head>
<body>
<h2>EPG XMLTV 节目表</h2>
<p>
<a href="epg_CN_0800.xml.gz">
下载 epg_CN_0800.xml.gz
</a>
</p>
<p>时区标记：+0800</p>
<p>已清理 tv date、programme desc、date、audio 节点。</p>
</body>
</html>
"""

    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print("Index:", INDEX_FILE)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 下载并解压原始 XML.GZ。
    compressed_data = download_source()
    xml_data = gzip.decompress(compressed_data)

    print("Original XML size:", len(xml_data))

    # 执行转换和节点清理。
    xml_data, stats = convert_xml(xml_data)

    # 验证 XML。
    validate_xml(xml_data)

    # 输出压缩文件和首页。
    write_gzip_file(xml_data)
    write_index()

    print("\n========== Conversion Summary ==========")
    for key, value in stats.items():
        print("{}: {}".format(key, value))

    print("Final XML size:", len(xml_data))
    print("========================================")


if __name__ == "__main__":
    main()
