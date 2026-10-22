import assert from "node:assert/strict";
import { createServer } from "node:http";
import { readFile, stat, mkdir, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { resolve, extname, sep } from "node:path";
import { chromium } from "playwright";

const root = resolve(fileURLToPath(new URL("../../../", import.meta.url)));
const mime = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".json": "application/json", ".png": "image/png" };
const server = createServer(async (req, res) => {
    try {
        const pathname = decodeURIComponent(new URL(req.url, "http://localhost").pathname);
        let path = resolve(root, "." + pathname);
        if (!path.startsWith(root + sep)) throw new Error("Invalid path");
        if ((await stat(path)).isDirectory()) path = resolve(path, "index.html");
        res.writeHead(200, { "Content-Type": mime[extname(path)] ?? "application/octet-stream" });
        res.end(await readFile(path));
    } catch { res.writeHead(404); res.end("Not found"); }
});
await new Promise(ready => server.listen(0, "127.0.0.1", ready));
const base = `http://127.0.0.1:${server.address().port}`;
const browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL || "chrome", headless: true });
const checks = [];
try {
    const page = await browser.newPage({ viewport: { width: 900, height: 900 } });
    const errors = [];
    page.on("pageerror", error => errors.push(String(error)));
    const open = async (layout, panel) => {
        const query = new URLSearchParams({ layout });
        if (panel) query.set("panel", panel);
        await page.goto(`${base}/runtimes/layaair3/example/?${query}`);
        await page.waitForFunction(() => window.PsdUiDemo?.ready || window.PsdUiDemo?.error, {}, { timeout: 60000 });
        const error = await page.evaluate(() => window.PsdUiDemo.error);
        assert.equal(error, undefined, error);
    };
    await open("/out/rules/layout.json");
    const fixture = await page.evaluate(() => {
        const root = PsdUiDemo.scene;
        const shop = root.getChildByName("Shop");
        const nested = shop.getChildByName("Nested");
        const canvas = root.drawToCanvas(320, 240, 0, 0);
        const pixels = [[35, 55], [55, 75], [75, 95], [215, 45], [305, 227]]
            .map(([x, y]) => Array.from(canvas.context.getImageData(x, y, 1, 1).data));
        return {
            version: Laya.LayaEnv.version,
            pixels, names: Array.from({ length: nested.numChildren }, (_, i) => nested.getChildAt(i).name),
            visibility: [root.getChildByName("Settings").visible, nested.getChildByName("Hidden").visible,
                shop.getChildByName("Baked").visible, shop.getChildByName("Hidden group").getChildByName("Locally visible").visible],
            text: shop.getChildByName("Title").text,
            bakedAlpha: shop.getChildByName("Baked").alpha,
        };
    });
    assert.equal(fixture.version, "3.4.1");
    assert.deepEqual(fixture.pixels, [[255, 0, 0, 255], [0, 255, 0, 255], [0, 0, 255, 255], [41, 51, 67, 255], [0, 0, 0, 0]]);
    assert.deepEqual(fixture.names, ["Red", "Green", "Blue", "Hidden"]);
    assert.deepEqual(fixture.visibility, [false, false, false, true]);
    assert.equal(fixture.text, "Shop\nUI");
    assert.equal(fixture.bakedAlpha, 1);
    checks.push("Real LayaAir 3.4.1: three-layer pixel overlap, local coordinates, hierarchy visibility, text, baked opacity");

    await open("/out/rules/layout.json", "Settings");
    assert.deepEqual(await page.evaluate(() => ({ count: PsdUiDemo.scene.numChildren,
        name: PsdUiDemo.scene.getChildAt(0).name, visible: PsdUiDemo.scene.getChildAt(0).visible,
        children: PsdUiDemo.scene.getChildAt(0).numChildren })),
    { count: 1, name: "Settings", visible: false, children: 2 });
    assert.match(await page.evaluate(async () => {
        try { await PsdUiDemo.PsdUiLoader.load("/out/rules/layout.json", { panelName: "missing" }); }
        catch (error) { return String(error); }
    }), /Expected one top-level panel/);
    checks.push("panelName selects only a top-level group and preserves hidden panel and descendants; missing panel rejects");

    await open("/out/test/layout.json");
    const real = await page.evaluate(async () => {
        const layout = await (await fetch("/out/test/layout.json")).json();
        let count = 0, images = 0, texts = 0;
        const check = (data, sprite) => {
            count++;
            for (const [actual, expected, key] of [[sprite.name, data.name, "name"],
                [sprite.visible, data.visible, "visible"], [sprite.x, data.position[0], "x"],
                [sprite.y, data.position[1], "y"], [sprite.width, data.size[0], "width"],
                [sprite.height, data.size[1], "height"]]) {
                if (actual !== expected) throw new Error(`${data.name}: ${key} ${actual} != ${expected}`);
            }
            if (data.type === "image") { images++; if (!sprite.texture) throw new Error("Missing texture"); }
            if (data.type === "text") { texts++; if (sprite.text !== data.text) throw new Error("Text mismatch"); }
            if (data.children) {
                if (sprite.numChildren !== data.children.length) throw new Error("Child count mismatch");
                data.children.forEach((child, i) => check(child, sprite.getChildAt(i)));
            }
        };
        check(layout, PsdUiDemo.scene);
        const canvas = PsdUiDemo.scene.drawToCanvas(layout.size[0], layout.size[1], 0, 0);
        return { count, images, texts, topLevel: layout.children.length, png: canvas.source.toDataURL("image/png") };
    });
    const expectedLayout = JSON.parse(await readFile(resolve(root, "out/test/layout.json"), "utf8"));
    const expected = { nodes: 0, images: 0, texts: 0 };
    const countNodes = node => {
        expected.nodes++;
        if (node.type === "image") expected.images++;
        if (node.type === "text") expected.texts++;
        node.children?.forEach(countNodes);
    };
    countNodes(expectedLayout);
    assert.equal(real.topLevel, expectedLayout.children.length);
    assert.equal(real.count, expected.nodes);
    assert.equal(real.texts, expected.texts);
    assert.equal(real.images, expected.images);
    await writeFile(resolve(root, "out/test/layaair-render.png"), Buffer.from(real.png.split(",")[1], "base64"));
    await page.addStyleTag({ content: "#status {display:none}" });
    await page.screenshot({ path: resolve(root, "out/test/layaair-preview.png") });
    checks.push(`test.psd: ${real.count} runtime nodes, ${real.images} images, ${real.texts} text nodes; all names/positions/sizes/visibility/children checked`);
    assert.deepEqual(errors, []);

    const missing = await browser.newPage();
    await missing.route("**/assets/Shop/Nested/Blue.png", route => route.fulfill({ status: 404, body: "missing" }));
    await missing.goto(`${base}/runtimes/layaair3/example/?layout=/out/rules/layout.json`);
    await missing.waitForFunction(() => window.PsdUiDemo?.error, {}, { timeout: 15000 });
    assert.match(await missing.evaluate(() => PsdUiDemo.error), /Missing PNG/);
    checks.push("Missing PNG rejects UI creation with a clear error");
    await mkdir(resolve(root, "out/validation"), { recursive: true });
    await writeFile(resolve(root, "out/validation/layaair.json"), JSON.stringify({ engine: "3.4.1", passed: checks }, null, 2) + "\n");
    console.log(checks.map(value => "PASS " + value).join("\n"));
} finally {
    await browser.close();
    await new Promise(done => server.close(done));
}

