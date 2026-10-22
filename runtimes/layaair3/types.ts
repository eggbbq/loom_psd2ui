export type Pair = [number, number];

interface BaseNode {
    name: string;
    position: Pair;
    size: Pair;
    visible: boolean;
}

export interface ContainerNode extends BaseNode {
    type: "container";
    /** Canonical LayaAir display node class, e.g. HBox, Button, List. */
    component?: string;
    layout?: "horizontal" | "vertical";
    gap?: number;
    children: UiNode[];
    opacity?: number;
}

export interface ImageNode extends BaseNode {
    type: "image";
    asset: string;
}

export interface TextNode extends BaseNode {
    type: "text";
    text: string;
    font?: string;
    fontSize?: number;
    color?: string;
    align: "left" | "center" | "right";
    outline: number;
    outlineColor?: string;
    shadow?: Pair;
    shadowColor?: string;
    shadowBlur?: number;
    opacity?: number;
}

export type UiNode = ContainerNode | ImageNode | TextNode;

export interface UiLayout extends BaseNode {
    version: 1;
    type: "root";
    children: UiNode[];
}

export interface LoadOptions {
    /** Defaults to the layout.json directory. Includes the assets/ prefix from JSON. */
    assetRoot?: string;
    /** Select one top-level container and preserve its position and visibility. */
    panelName?: string;
    onWarning?: (message: string) => void;
}

