import { PsdUiLoader } from "../PsdUiLoader";

export { PsdUiLoader };
export let scene: Laya.Sprite;
export let error: string | undefined;
export let ready = false;

async function main() {
    const params = new URLSearchParams(location.search);
    const layoutUrl = params.get("layout") ?? "/out/test/layout.json";
    const metadata = await (await fetch(layoutUrl)).json();
    await Laya.init({ designWidth: metadata.size[0], designHeight: metadata.size[1],
                      scaleMode: Laya.Stage.SCALE_SHOWALL });
    Laya.stage.bgColor = "#30363D";
    scene = await PsdUiLoader.load(layoutUrl, {
        panelName: params.get("panel") ?? undefined,
        assetRoot: params.get("assets") ?? undefined,
    });
    Laya.stage.addChild(scene);
    document.getElementById("status")!.textContent = `LayaAir 3.4.1 · ${metadata.name}\n${params.get("panel") ?? "全部 panel（保留 PSD 可见性）"}`;
    ready = true;
}

main().catch(reason => {
    error = String(reason?.stack ?? reason);
    document.getElementById("status")!.textContent = error;
    console.error(reason);
});

