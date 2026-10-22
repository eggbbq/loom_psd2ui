from .paths import inside, load_json


MANIFEST = ".ninegrid/manifest.json"


def read_manifest(root):
    data = load_json(inside(root, MANIFEST))
    if data.get("schemaVersion") != 1 or not isinstance(data.get("items"), list):
        raise ValueError("Unsupported manifest format")
    seen = set()
    for item in data["items"]:
        for key in ("source", "output"):
            path = inside(root, item[key])
            if not path.is_relative_to(inside(root, "assets")):
                raise ValueError("Manifest textures must be project assets")
            if (key, item[key]) in seen:
                raise ValueError("Duplicate manifest path")
            seen.add((key, item[key]))
        if item.get("overwriteSource"):
            if item["source"] != item["output"]:
                raise ValueError("In-place output must be the source PNG")
            for key, directory in (("originalBackup", ".ninegrid/originals"), ("stagedOutput", ".ninegrid/staged")):
                if not inside(root, item[key]).is_relative_to(inside(root, directory)):
                    raise ValueError("Invalid in-place backup/staging path")
        elif item["source"] == item["output"]:
            raise ValueError("Manifest cannot overwrite originals")
    return data


def markdown_report(report):
    lines = ["# NineGrid 优化报告", "", "节省率表示纹理像素面积，非文件大小或 DrawCall。", "",
             "| 图片 | 状态 | 原始尺寸 | 优化尺寸 | 面积节省 | 原因 |",
             "|---|---|---|---|---|---|"]
    for item in report["items"]:
        source = item["source"].replace("|", "\\|")
        size = "×".join(map(str, item.get("sourceSize", [])))
        optimized = "×".join(map(str, item.get("outputSize", [])))
        lines.append(f"| {source} | {item['status']} | {size} | {optimized} | "
                     f"{item.get('pixelAreaSavedRatio', 0):.3%} | {item.get('reason') or ''} |")
    visual = [item for item in report["items"] if item.get("mode") == "visual"]
    if visual:
        lines += ["", "## 视觉近似结果", "", "这是允许像素变化的模式，不宣称逐像素无损。", "",
                  "| 图片 | 拉伸方式 | 平均误差 / 255 | 严重误差像素占比 |",
                  "|---|---|---|---|"]
        for item in visual:
            quality = item["cpuQuality"]
            lines.append(f"| {item['source'].replace('|', ' ')} | {item['sliceMode']} | "
                         f"{quality['meanError']:.4f} | {quality['badPixelRatio']:.4%} |")
    return "\n".join(lines) + "\n"
