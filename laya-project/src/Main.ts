const { regClass } = Laya;

/** Optional user script. UI hierarchy is authored in assets/PSD2UI/test.lh. */
@regClass()
export class Main extends Laya.Script {
    onStart(): void {
        console.info("PSD2UI: UI is loaded from the native prefab.");
    }
}
