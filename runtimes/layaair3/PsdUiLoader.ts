import type { LoadOptions, UiLayout, UiNode } from "./types";

/** Runtime adapter verified against LayaAir 3.4.1's real declarations and engine. */
export class PsdUiLoader {
    static async load(layoutUrl: string, options: LoadOptions = {}): Promise<Laya.Sprite> {
        const url = new URL(layoutUrl, document.baseURI);
        const response = await fetch(url.href);
        if (!response.ok) throw new Error(`Cannot load ${url}: HTTP ${response.status}`);
        const layout: UiLayout = await response.json();
        this.validate(layout);
        const assets = new URL(options.assetRoot ?? ".", url);
        if (!assets.pathname.endsWith("/")) assets.pathname += "/";
        const warn = options.onWarning ?? console.warn;
        const fonts = new Set<string>();
        let children = layout.children;
        if (options.panelName !== undefined) {
            const panels = children.filter(n => n.type === "container" && n.name === options.panelName);
            if (panels.length !== 1) throw new Error(`Expected one top-level panel '${options.panelName}', found ${panels.length}`);
            children = panels;
        }
        const root = new Laya.Sprite();
        root.name = layout.name;
        root.pos(...layout.position);
        root.size(...layout.size);
        root.visible = layout.visible;
        try {
            for (let index = 0; index < children.length; index++) {
                const child = await this.create(children[index], assets, warn, fonts);
                child.zOrder = index;
                root.addChild(child);
            }
            return root;
        } catch (error) {
            root.destroy(true);
            throw error;
        }
    }

    private static async create(node: UiNode, assets: URL, warn: (message: string) => void,
                                fonts: Set<string>): Promise<Laya.Sprite> {
        const sprite = node.type === "text" ? new Laya.Text() : new Laya.Sprite();
        try {
            sprite.name = node.name;
            sprite.pos(...node.position);
            sprite.size(...node.size);
            sprite.visible = node.visible;
            if ("opacity" in node && node.opacity !== undefined) sprite.alpha = node.opacity;
            if (node.type === "image") {
                const url = new URL(node.asset.split("/").map(encodeURIComponent).join("/"), assets).href;
                const texture = await Laya.loader.load(url, Laya.Loader.IMAGE) as Laya.Texture;
                if (!texture) throw new Error(`Missing PNG: ${url}`);
                sprite.texture = texture;
            } else if (node.type === "text") {
                const text = sprite as Laya.Text;
                text.text = node.text;
                text.font = node.font ?? "Arial";
                text.fontSize = node.fontSize ?? 12;
                text.color = node.color ?? "#000000";
                text.align = node.align;
                text.valign = "top";
                text.padding = [0, 0, 0, 0];
                text.wordWrap = false;
                text.overflow = Laya.Text.VISIBLE;
                text.stroke = node.outline;
                if (node.outlineColor) text.strokeColor = node.outlineColor;
                if (node.shadow) {
                    text.shadowOffsetX = node.shadow[0];
                    text.shadowOffsetY = node.shadow[1];
                    if (node.shadowColor) text.shadowColor = node.shadowColor;
                    if (node.shadowBlur !== undefined) text.shadowBlur = node.shadowBlur;
                }
                if (!node.font || !node.fontSize || !node.color) warn(`Text '${node.name}' has incomplete PSD styles; using runtime defaults`);
                if (node.font && !fonts.has(node.font)) {
                    fonts.add(node.font);
                    warn(`PSD font '${node.font}' must be installed or registered before loading; fallback fonts change metrics`);
                }
            } else {
                for (let index = 0; index < node.children.length; index++) {
                    const child = await this.create(node.children[index], assets, warn, fonts);
                    child.zOrder = index;
                    sprite.addChild(child);
                }
            }
            return sprite;
        } catch (error) {
            sprite.destroy(true);
            throw error;
        }
    }

    private static validate(layout: UiLayout): void {
        if (layout.version !== 1 || layout.type !== "root") throw new Error("Unsupported PSD2UI layout version/type");
        const visit = (node: UiLayout | UiNode, root = false): void => {
            if (!node || typeof node.name !== "string" || typeof node.visible !== "boolean") throw new Error("Invalid node identity/visibility");
            for (const key of ["position", "size"] as const) {
                if (!Array.isArray(node[key]) || node[key].length !== 2 || !node[key].every(Number.isFinite)) throw new Error(`Invalid ${key}: ${node.name}`);
            }
            if (node.size.some(v => v < 0)) throw new Error(`Negative size: ${node.name}`);
            if ("opacity" in node && node.opacity !== undefined && (!Number.isFinite(node.opacity) || node.opacity < 0 || node.opacity > 1)) throw new Error(`Invalid opacity: ${node.name}`);
            if ((root && node.type === "root") || node.type === "container") {
                if (!("children" in node) || !Array.isArray(node.children)) throw new Error(`Missing children: ${node.name}`);
                node.children.forEach(child => visit(child));
            } else if (node.type === "image") {
                if (typeof node.asset !== "string" || !node.asset.endsWith(".png") ||
                    node.asset.split("/").some(part => !part || part === "." || part === "..") ||
                    /[\\:#?\x00-\x1f]/.test(node.asset)) throw new Error(`Unsafe asset path: ${node.name}`);
            } else if (node.type === "text") {
                if (typeof node.text !== "string" || !["left", "center", "right"].includes(node.align)) throw new Error(`Invalid text: ${node.name}`);
            } else throw new Error(`Unknown node type: ${node.name}`);
        };
        visit(layout, true);
    }
}

