import assert from "node:assert/strict";
import { createServer } from "node:http";
import { readFile, stat, writeFile, mkdir } from "node:fs/promises";
import { resolve, extname, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";
import { execFileSync } from "node:child_process";

const root = resolve(fileURLToPath(new URL("../../../", import.meta.url)));
// Exercise the PSD -> layout -> .lh pipeline with every special container tag.
const taggedFixture = JSON.parse(execFileSync(resolve(root, ".venv/bin/python"), ["-c", `
import base64, json, tempfile
from pathlib import Path
from tests.fixture_factory import make_tag_fixture
from psd2ui.exporter import export_psd
from psd2ui.laya_prefab import generate_prefab
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory)
    export_psd(make_tag_fixture(path / "tags.psd", extended=True), path / "out")
    (path / "project").mkdir()
    result = generate_prefab(path / "out/layout.json", path / "project")
    textures = {}
    for image in (path / "project/assets").rglob("*.png"):
        uuid = json.loads(image.with_suffix(".png.meta").read_text())["uuid"]
        textures[uuid] = "data:image/png;base64," + base64.b64encode(image.read_bytes()).decode()
    print(json.dumps({"prefab": json.loads(Path(result["prefab"]).read_text()), "textures": textures}))
`], { cwd: root, encoding: "utf8" }));
const release = resolve(root, "laya-project/release/web");
const expectedLayout = JSON.parse(await readFile(resolve(root, "out/test/layout.json"), "utf8"));
const scene = JSON.parse(await readFile(resolve(root, "laya-project/assets/Scene.ls"), "utf8"));
const sceneExtras = scene._$child.find(node => node._$prefab === "0f89a340-1749-53d0-bf0e-ee9dfda731ce")?._$child ?? [];
const expectedCounts = { total: 0, images: 0, texts: 0 };
function countLayout(node) {
    expectedCounts.total++;
    if (node.type === "image") expectedCounts.images++;
    if (node.type === "text") expectedCounts.texts++;
    node.children?.forEach(countLayout);
}
countLayout(expectedLayout);
const mime = { ".html": "text/html", ".js": "text/javascript", ".json": "application/json", ".ls": "application/json", ".png": "image/png" };
const server = createServer(async (req, res) => {
    try {
        let path = resolve(release, "." + decodeURIComponent(new URL(req.url, "http://localhost").pathname));
        if (path !== release && !path.startsWith(release + sep)) throw new Error("Invalid path");
        if ((await stat(path)).isDirectory()) path = resolve(path, "index.html");
        res.writeHead(200, { "Content-Type": mime[extname(path)] ?? "application/octet-stream" });
        res.end(await readFile(path));
    } catch { res.writeHead(404); res.end("Not found"); }
});
await new Promise(ready => server.listen(0, "127.0.0.1", ready));
const browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL || "chrome" });
try {
    const urls = [`http://127.0.0.1:${server.address().port}/`];
    if (process.env.PSD2UI_LAYA_PREVIEW_URL) urls.push(process.env.PSD2UI_LAYA_PREVIEW_URL);
    const results = [];
    for (const url of urls) {
        const page = await browser.newPage({ viewport: { width: 900, height: 900 } });
        const errors = [];
        const requests = [];
        page.on("pageerror", error => errors.push(String(error)));
        page.on("request", request => requests.push(request.url()));
        page.on("response", response => {
            if (response.status() >= 400 && !response.url().endsWith("favicon.ico")) errors.push(`${response.status()}: ${response.url()}`);
        });
        await page.goto(url);
        await page.waitForFunction((name) => {
            const find = node => node?.name === name ? node :
                Array.from({ length: node?.numChildren ?? 0 }, (_, i) => find(node.getChildAt(i))).find(Boolean);
            const ui = find(window.Laya?.stage);
            const loaded = node => (!((node instanceof Laya.GImage || node instanceof Laya.GLoader) && node.src) || !!node.texture) &&
                Array.from({ length: node.numChildren }, (_, i) => loaded(node.getChildAt(i))).every(Boolean);
            return ui && loaded(ui);
        }, expectedLayout.name, { timeout: 60000 });
        const result = await page.evaluate(async (layout) => {
            const find = node => node?.name === layout.name ? node :
                Array.from({ length: node?.numChildren ?? 0 }, (_, i) => find(node.getChildAt(i))).find(Boolean);
            const ui = find(Laya.stage);
            let total = 0, images = 0, texts = 0;
            // GTextField/GLoader own engine-created children that are omitted
            // from .lh files; compare the serialized PSD hierarchy only.
            const childrenOf = node => Array.from({ length: node.numChildren }, (_, i) => node.getChildAt(i))
                .filter(child => !(child.hideFlags & 2));
            const check = (data, sprite) => {
                total++;
                if ((data.type === "container" || data.type === "root") && sprite.constructor !== Laya[data.component ?? "GWidget"])
                    throw new Error(`${data.name}: expected Laya.${data.component ?? "GWidget"}`);
                for (const [actual, expected, field] of [[sprite.name, data.name, "name"],
                    [sprite.visible, data.visible, "visible"], [sprite.x, data.position[0], "x"],
                    [sprite.y, data.position[1], "y"], [sprite.width, data.size[0], "width"], [sprite.height, data.size[1], "height"]]) {
                    if (actual !== expected) throw new Error(`${data.name}: wrong ${field}`);
                }
                if (data.type === "image") {
                    images++;
                    const type = data.component ?? "GImage";
                    if (sprite.constructor !== Laya[type]) throw new Error(`${data.name}: expected Laya.${type}`);
                    const texture = sprite.background?.texture ?? sprite.texture;
                    if (!texture) throw new Error(`${data.name}: missing image texture`);
                    if (sprite.autoSize) throw new Error(`${data.name}: expected explicit layout size`);
                    if (texture.sourceWidth !== data.size[0] || texture.sourceHeight !== data.size[1])
                        throw new Error(`${data.name}: wrong source dimensions`);
                }
                if (data.type === "text") {
                    texts++;
                    if (!(sprite instanceof Laya.GTextField)) throw new Error(`${data.name}: expected GTextField`);
                    if (sprite.text !== data.text) throw new Error("Wrong text");
                }
                if (data.children) {
                    const children = childrenOf(sprite);
                    if (data.children.length + (data.type === "root" ? layout.sceneExtraCount : 0) !== children.length)
                        throw new Error("Wrong children count");
                    data.children.forEach((child, i) => check(child, children[i]));
                }
            };
            check(layout, ui);
            return { version: Laya.LayaEnv.version, startupScene: ui.parent.name, root: ui.name,
                topLevel: ui.numChildren, total, images, texts };
        }, { ...expectedLayout, sceneExtraCount: sceneExtras.length });
        assert.deepEqual(result, { version: "3.4.1", startupScene: "PSD2UI", root: expectedLayout.name,
            topLevel: expectedLayout.children.length + sceneExtras.length, ...expectedCounts });
        // Regression: compare the unmodified prefab Text's actual glyph pixels,
        // not just JSON/node coordinates (which used to agree while drawing too low).
        const lv10 = await page.evaluate(() => {
            const find = node => node?.name === "test" ? node :
                Array.from({ length: node?.numChildren ?? 0 }, (_, i) => find(node.getChildAt(i))).find(Boolean);
            const ui = find(Laya.stage);
            const avatar = ui.getChildByName("状态栏").getChildByName("头像");
            const text = Array.from({ length: avatar.numChildren }, (_, i) => avatar.getChildAt(i))
                .find(node => node instanceof Laya.GTextField && node.text === "Lv 10");
            const position = text.localToGlobal(new Laya.Point(0, 0), false, ui);
            const oldParent = text.parent;
            const oldIndex = oldParent.getChildIndex(text);
            const oldPosition = [text.x, text.y];
            const holder = new Laya.Sprite();
            let fill;
            try {
                holder.addChild(text);
                text.pos(position.x, position.y);
                const canvas = holder.drawToCanvas(180, 180, 0, 0);
                const pixels = canvas.context.getImageData(0, 0, 180, 180).data;
                let left = 180, top = 180, right = -1, bottom = -1;
                for (let y = 0; y < 180; y++) for (let x = 0; x < 180; x++) {
                    const i = (y * 180 + x) * 4;
                    if (pixels[i] > 200 && pixels[i + 1] > 200 && pixels[i + 2] > 200 && pixels[i + 3] > 128) {
                        left = Math.min(left, x); top = Math.min(top, y);
                        right = Math.max(right, x); bottom = Math.max(bottom, y);
                    }
                }
                fill = [left, top, right + 1, bottom + 1];
            } finally {
                oldParent.addChildAt(text, oldIndex);
                text.pos(...oldPosition);
                holder.destroy();
            }
            return { nodeOrigin: [position.x, position.y], glyphBounds: fill, font: text.font, fontSize: text.fontSize };
        });
        assert.deepEqual(lv10.nodeOrigin, [36, 104]);
        assert.deepEqual(lv10.glyphBounds, [39, 116, 119, 138], "Lv 10 glyph pixels must match the PSD ink bounds");
        const taggedContainers = await page.evaluate(async ({ prefab: data, textures }) => {
            await Promise.all(Object.values(textures).map(src => Laya.loader.load(src, Laya.Loader.IMAGE)));
            const replaceReferences = node => {
                if (node?.src?.startsWith("res://")) node.src = textures[node.src.slice(6)];
                if (node?._$uuid && textures[node._$uuid]) node._$uuid = textures[node._$uuid];
                if (node && typeof node === "object") Object.values(node).forEach(replaceReferences);
            };
            replaceReferences(data);
            const errors = [];
            const ui = new Laya.PrefabImpl(null, data).create(null, errors);
            ui.visible = false;
            Laya.stage.addChild(ui);
            try {
                await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
                const result = ["Row", "Column", "Window"].map((name, index) => {
                    const node = ui.getChildByName(name);
                    const type = ["GBox", "GBox", "GPanel"][index];
                    if (node.constructor !== Laya[type]) throw new Error(`${name}: wrong native container`);
                    return { type, gap: index === 0 ? node.layout.columnGap : index === 1 ? node.layout.rowGap : null,
                        children: Array.from({ length: node.numChildren }, (_, i) => {
                        const child = node.getChildAt(i);
                        return [child.name, child.x, child.y];
                    }) };
                });
                const types = { ShortPanel: "GPanel", Button: "GButton", ShortButton: "GButton", List: "GList",
                    Progress: "GProgressBar", ShortProgress: "GProgressBar", Combo: "GComboBox", Slider: "GSlider", Loader: "GLoader",
                    Icon: "GLoader", ShortIcon: "GLoader", Generic: "GLabel", Exact: "GButton", NativeImage: "GImage", Leaf: "GButton",
                    Caption: "GTextField", Heading: "GTextField", Account: "GTextInput",
                    ChineseBackground: "GImage", ChineseButton: "GButton", ChineseTitle: "GTextField",
                    ChineseBorder: "GImage", ChineseIcon: "GLoader", ChineseImage: "GImage",
                    ChineseTrim: "GImage", ChineseBase: "GImage" };
                for (const [name, type] of Object.entries(types)) {
                    const node = ui.getChildByName(name);
                    if (node.constructor !== Laya[type]) throw new Error(`${name}: expected ${type}`);
                    if (["Loader", "Icon", "ShortIcon", "NativeImage", "ChineseBackground", "ChineseBorder",
                        "ChineseIcon", "ChineseImage", "ChineseTrim", "ChineseBase"].includes(name) && !node.texture)
                        throw new Error(`${name}: missing New UI texture`);
                }
                for (const name of ["Button", "ShortButton", "Exact", "Progress", "ShortProgress", "ChineseButton"]) {
                    const control = ui.getChildByName(name);
                    if (control.getChildAt(0).name !== "title" || control.getChildAt(1).name !== "title")
                        throw new Error(`${name}: fallback text must be named title`);
                    if (control.getChildAt(0).text !== "A" || control.getChildAt(1).text !== "B")
                        throw new Error(`${name}: renamed text lost its content`);
                }
                if (ui.getChildByName("Caption").text !== "UI" || ui.getChildByName("Account").text !== "Account" ||
                    ui.getChildByName("ChineseTitle").text !== "Heading")
                    throw new Error("New UI text aliases lost their editable text");
                if (errors.length) throw new Error(JSON.stringify(errors));
                return { layouts: result, types };
            } finally { ui.destroy(true); }
        }, taggedFixture);
        assert.deepEqual(taggedContainers.layouts, [
            { type: "GBox", gap: 15, children: [["text", 0, 0], ["text", 105, 0]] },
            { type: "GBox", gap: 12, children: [["text", 0, 0], ["text", 0, 44]] },
            { type: "GPanel", gap: null, children: [["text", 0, 0], ["text", 15, 10]] },
        ]);
        assert.deepEqual(errors, []);
        assert.equal(requests.filter(url => /\/layout\.json(?:\?|$)/.test(url)).length, 0,
            "Native scene must not fetch runtime layout.json");
        if (results.length === 0) assert(requests.some(url => url.endsWith("/PSD2UI/test.lh")), "Scene must reference the native prefab");
        await page.waitForFunction(() => !document.getElementById("splash"), {}, { timeout: 10000 });
        await page.screenshot({ path: resolve(root, "out/validation/laya-project-web.png") });
        results.push({ mode: results.length ? "IDE CLI preview" : "native Web build", ...result, runtimeLayoutRequests: 0, lv10, taggedContainers });
        await page.close();
    }
    await mkdir(resolve(root, "out/validation"), { recursive: true });
    await writeFile(resolve(root, "out/validation/native-project.json"), JSON.stringify({ passed: results }, null, 2) + "\n");
    console.log(JSON.stringify(results, null, 2));
} finally {
    await browser.close();
    await new Promise(done => server.close(done));
}

