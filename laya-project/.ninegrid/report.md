# NineGrid 优化报告

节省率表示纹理像素面积，非文件大小或 DrawCall。

| 图片 | 状态 | 原始尺寸 | 优化尺寸 | 面积节省 | 原因 |
|---|---|---|---|---|---|
| assets/ui/test/toasts/bg.png | candidate | 550×110 | 30×30 | 98.512% |  |
| assets/ui/test/任务/bg.png | candidate | 889×1110 | 263×414 | 88.966% |  |
| assets/ui/test/任务/buttons/daliy_quest/save.png | skipped | 60×58 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/任务/buttons/main_quest/sward.png | skipped | 70×68 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/任务/图层 1263.png | skipped | 750×704 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/任务/图层 1264.png | skipped | 900×531 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/任务/矩形 1266.png | candidate | 1092×798 | 10×10 | 99.989% |  |
| assets/ui/test/任务/组 31/item/bg.png | candidate | 629×127 | 16×23 | 99.539% |  |
| assets/ui/test/任务/组 31/item/item/bg_item.png | candidate | 80×80 | 14×14 | 96.938% |  |
| assets/ui/test/任务/组 31/item/item/wood 拷贝.png | skipped | 38×48 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/任务/组 31/item/ok 拷贝.png | skipped | 40×34 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/任务/组 31/item/progress/progress_bar 拷贝/bg/矩形 42.png | candidate | 310×24 | 10×10 | 98.656% |  |
| assets/ui/test/任务/组 31/item/progress/progress_bar 拷贝/fill.png | candidate | 304×18 | 10×18 | 96.711% |  |
| assets/ui/test/任务/组 31/item 拷贝 10/claim/2.png | skipped | 161×79 | 16×24 | 96.981% | shared_source_has_unsafe_references |
| assets/ui/test/任务/组 31/item 拷贝 10/item/bg_item.png | candidate | 80×80 | 14×14 | 96.938% |  |
| assets/ui/test/任务/组 31/item 拷贝 7/bg.png | candidate | 629×128 | 16×24 | 99.523% |  |
| assets/ui/test/任务/组 31/item 拷贝 7/claim/2.png | skipped | 161×79 | 16×24 | 96.981% | shared_source_has_unsafe_references |
| assets/ui/test/任务/组 31/item 拷贝 7/progress/progress_bar 拷贝/fill/矩形 43 拷贝 2.png | candidate | 304×14 | 10×14 | 96.711% |  |
| assets/ui/test/任务/组 31/item 拷贝 7/progress/progress_bar 拷贝/fill/矩形 43.png | candidate | 304×18 | 10×10 | 98.173% |  |
| assets/ui/test/任务/组 31/item 拷贝 8/claim/2.png | skipped | 161×79 | 16×24 | 96.981% | shared_source_has_unsafe_references |
| assets/ui/test/任务/组 31/item 拷贝 8/progress/progress_bar 拷贝/bg/矩形 41.png | candidate | 150×14 | 10×14 | 93.333% |  |
| assets/ui/test/任务/组 31/item 拷贝 8/progress/progress_bar 拷贝/fill.png | candidate | 77×18 | 10×18 | 87.013% |  |
| assets/ui/test/任务/组 31/item 拷贝 9/claim/2.png | skipped | 161×80 | 16×25 | 96.894% | shared_source_has_unsafe_references |
| assets/ui/test/制造样式1/列表/组 29 拷贝 9/item/bed.png | skipped | 40×60 | 20×43 | 64.167% | shared_source_has_unsafe_references |
| assets/ui/test/制造样式1/列表/组 29 拷贝 9/item 拷贝/build.png | skipped | 40×64 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/制造样式1/列表/问号.png | skipped | 41×68 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/制造样式1/材料预览/bg_item.png | skipped | 350×250 | 14×14 | 99.776% | shared_source_has_unsafe_references |
| assets/ui/test/制造样式1/材料预览/材料1/block.png | skipped | 30×36 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/制造样式1/配方/底板.png | skipped | 889×1110 | 263×666 | 82.250% | shared_source_has_unsafe_references |
| assets/ui/test/制造样式1/页码提示/矩形 1073 拷贝 2.png | skipped | 11×12 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/制造样式1/页码提示/矩形 1073 拷贝.png | skipped | 11×12 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/制造样式1/页码提示/矩形 1073.png | skipped | 10×12 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/制造样式2/确定取消 拷贝 2/item 拷贝 20/bg_item.png | skipped | 80×80 | 14×14 | 96.938% | shared_source_has_unsafe_references |
| assets/ui/test/制造样式2/确定取消 拷贝 2/no/x.png | skipped | 40×38 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/制造样式2/确定取消 拷贝 2/no/矩形 1431 拷贝.png | skipped | 80×80 | 14×14 | 96.938% | shared_source_has_unsafe_references |
| assets/ui/test/功能解锁/item 拷贝 15/book.png | skipped | 46×60 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/场景/图层 18.png | skipped | 3154×1725 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/场景/图层 1864.png | candidate | 611×197 | 489×165 | 32.968% |  |
| assets/ui/test/存储/bg.png | candidate | 889×1300 | 262×774 | 82.453% |  |
| assets/ui/test/存储/buttons/back/back.png | skipped | 53×48 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/存储/buttons/三角形 1477.png | skipped | 26×22 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/存储/箱子列表/grid/组 29 拷贝 3/item/bg_item.png | skipped | 100×100 | 14×14 | 98.040% | shared_source_has_unsafe_references |
| assets/ui/test/存储/背包.png | candidate | 667×329 | 581×243 | 35.663% |  |
| assets/ui/test/存储 拷贝/bg.png | candidate | 889×1300 | 262×664 | 84.947% |  |
| assets/ui/test/对话样式1/build/1.png | skipped | 669×90 | 50×52 | 95.682% | shared_source_has_unsafe_references |
| assets/ui/test/对话样式1/destory/1.png | skipped | 669×89 | 50×51 | 95.717% | shared_source_has_unsafe_references |
| assets/ui/test/对话样式1/底部（对话）/build/2.png | skipped | 663×79 | 18×24 | 99.175% | shared_source_has_unsafe_references |
| assets/ui/test/对话样式1/模型/图层 1190.png | skipped | 176×277 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/对话样式1/模型/图层 1191.png | skipped | 339×275 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/对话样式2/底部（对话）/destroy/levelup.png | skipped | 38×56 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/底部（升级）/yes/levelup.png | skipped | 45×66 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/底部（升级）/价格/gold.png | skipped | 44×50 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/底部（升级）/升级时间/clock.png | skipped | 48×52 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/底部（建造中）/状态/build.png | skipped | 39×63 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/底部（树木.取消）/pause.png | skipped | 16×16 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/底部（树木.砍伐）/arrow.png | skipped | 26×42 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/底部（树木.砍伐）/bg_item.png | skipped | 710×310 | 30×30 | 99.591% | shared_source_has_unsafe_references |
| assets/ui/test/底部（树木.砍伐）/yes/foutou2.png | skipped | 39×63 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/底部（树木.砍伐）/yes/矩形 18 拷贝 3.png | skipped | 106×120 | 36×48 | 86.415% | shared_source_has_unsafe_references |
| assets/ui/test/底部（流民.招募）/gold/gold.png | skipped | 46×52 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/底部（流民.招募）/yes/copy.png | skipped | 46×60 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/底部（流民.招募）/新手引导2 拷贝/toasts 拷贝 2/bg.png | candidate | 400×90 | 30×30 | 97.500% |  |
| assets/ui/test/底部（流民.招募）/新手引导2 拷贝/图层 777.png | skipped | 111×215 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/底部（流民.招募）/新手引导2 拷贝/图层 788.png | skipped | 147×84 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/底部（进入）/yes/foot.png | skipped | 66×72 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/底部（锁住的门）/materals/bg_item.png | candidate | 110×110 | 30×30 | 92.562% |  |
| assets/ui/test/底部（锁住的门）/yes/key.png | skipped | 45×72 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/建造列表/三角形 1477 拷贝.png | skipped | 26×22 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/建造列表/列表/组 29 拷贝 9/item/bg_item.png | candidate | 280×337 | 218×270 | 37.622% |  |
| assets/ui/test/建造列表/列表/组 29 拷贝 9/item/coin/yb.png | skipped | 22×25 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/建造列表/列表/组 29 拷贝 9/item/组 33.png | skipped | 209×147 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/建造列表/列表/组 29 拷贝 9/item 拷贝 19/组 33.png | skipped | 210×149 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/建造列表/网格线/图层 1426.png | skipped | 178×138 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/建造列表/网格线/图层 1428 拷贝 4.png | skipped | 207×108 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/建造列表/网格线/图层 1428.png | skipped | 209×118 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/建造列表/网格线/矩形 1428.png | candidate | 211×110 | 30×104 | 86.558% |  |
| assets/ui/test/建造列表/配方/底板.png | candidate | 889×1110 | 263×618 | 83.529% |  |
| assets/ui/test/建造列表/页码提示/矩形 1073 拷贝 2.png | skipped | 11×11 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/建造列表/页码提示/矩形 1073 拷贝.png | skipped | 11×11 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/建造列表/页码提示/矩形 1073.png | skipped | 10×11 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/弹窗遮罩.png | candidate | 750×1623 | 10×10 | 99.992% |  |
| assets/ui/test/恭喜获得/bg_恭喜获得.png | candidate | 750×384 | 653×283 | 35.834% |  |
| assets/ui/test/恭喜获得/item/bg_item.png | candidate | 110×110 | 14×14 | 98.380% |  |
| assets/ui/test/恭喜获得/弹窗遮罩 拷贝 2.png | candidate | 750×1623 | 10×10 | 99.992% |  |
| assets/ui/test/战斗结束/胜/说明/组 34.png | skipped | 675×148 | 14×13 | 99.818% | shared_source_has_unsafe_references |
| assets/ui/test/战斗结束/败/场景 拷贝.png | skipped | 3154×1725 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/抽卡/卡牌.png | skipped | 142×158 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/抽卡/卡牌属性/frame.png | candidate | 280×100 | 30×30 | 96.786% |  |
| assets/ui/test/抽卡/卡牌属性/kulou.png | skipped | 48×48 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/抽卡/卡牌详情.png | skipped | 242×302 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/抽卡/图层 20.png | skipped | 1476×1624 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/抽卡/图层 21.png | candidate | 750×1624 | 636×1345 | 29.768% |  |
| assets/ui/test/抽卡/图层 23.png | skipped | 750×1275 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/抽卡/图层 24.png | skipped | 1378×1556 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/抽卡/弹窗遮罩 拷贝.png | candidate | 750×1623 | 10×10 | 99.992% |  |
| assets/ui/test/抽卡/矩形 49.png | candidate | 596×320 | 10×10 | 99.948% |  |
| assets/ui/test/抽卡/组 19/图层 29.png | skipped | 732×1239 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/抽卡/组 27 拷贝 2.png | skipped | 617×176 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/抽卡/组 27 拷贝 3.png | skipped | 630×176 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/抽卡/组 27 拷贝.png | skipped | 604×176 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/抽卡/组 27.png | skipped | 768×176 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/新手引导/hand.png | skipped | 64×84 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/新手引导/toasts 拷贝/bg.png | candidate | 630×160 | 30×30 | 99.107% |  |
| assets/ui/test/新手引导/椭圆 776.png | candidate | 238×240 | 10×10 | 99.825% |  |
| assets/ui/test/新手引导/矩形 775.png | candidate | 750×1624 | 370×552 | 83.232% |  |
| assets/ui/test/暂停/bg_content/矩形 3 拷贝.png | candidate | 514×276 | 10×10 | 99.930% |  |
| assets/ui/test/暂停/bg_win.png | candidate | 584×519 | 62×57 | 98.834% |  |
| assets/ui/test/暂停/close/x.png | skipped | 60×57 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/暂停/exit/1.png | skipped | 469×100 | 50×52 | 94.456% | shared_source_has_unsafe_references |
| assets/ui/test/暂停/resume/2.png | skipped | 469×99 | 50×51 | 94.508% | shared_source_has_unsafe_references |
| assets/ui/test/暂停/title/bg 拷贝 2.png | skipped | 623×170 | 197×122 | 77.307% | shared_source_has_unsafe_references |
| assets/ui/test/暂停/tog_bgm/bgm_off.png | skipped | 44×51 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/暂停/tog_sfx/sfx_off.png | skipped | 40×44 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/暂停/tog_sfx/sfx_on.png | skipped | 28×45 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/状态栏/任务/book.png | skipped | 48×60 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/状态栏/体力/meat.png | skipped | 56×48 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/状态栏/头像/avatar_girl_1.png | skipped | 58×58 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/状态栏/心/heart 拷贝 25.png | skipped | 352×24 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/状态栏/心/heart 拷贝 26.png | skipped | 678×24 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/状态栏/背包/bag.png | skipped | 52×52 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/组 36/底部（树木.取消） 拷贝/wakeup/eye.png | skipped | 53×51 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/组 36/组 35/图层 1884.png | candidate | 784×982 | 677×896 | 21.210% |  |
| assets/ui/test/组 36/组 35/图层 1886.png | skipped | 592×732 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/组 36/组 35/图层 1887 拷贝.png | skipped | 750×1116 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/组 36/组 35/图层 1887.png | skipped | 750×1405 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/组 36/组 35/矩形 1886.png | candidate | 827×1742 | 10×10 | 99.993% |  |
| assets/ui/test/组件/progress_bar/bg/矩形 41.png | candidate | 260×24 | 10×10 | 98.397% |  |
| assets/ui/test/组件/progress_bar/bg/矩形 42.png | candidate | 250×34 | 10×10 | 98.824% |  |
| assets/ui/test/组件/progress_bar/fill.png | candidate | 168×28 | 15×28 | 91.071% |  |
| assets/ui/test/背包/组 28/add/add.png | skipped | 48×48 | 40×38 | 34.028% | shared_source_has_unsafe_references |
| assets/ui/test/背包/组 28/add/矩形 34 拷贝 2.png | candidate | 104×104 | 10×10 | 99.075% |  |
| assets/ui/test/背包/组 28/item_bg.png | candidate | 667×328 | 581×242 | 35.732% |  |
| assets/ui/test/背包/组 28/items/item/meat.png | skipped | 70×60 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/背包/组 28/items/item/矩形 1188.png | candidate | 103×102 | 10×10 | 99.048% |  |
| assets/ui/test/背包/组 28/items/item 拷贝 5/矩形 1188.png | candidate | 103×103 | 10×10 | 99.057% |  |
| assets/ui/test/背包/选中框 拷贝.png | candidate | 100×100 | 30×30 | 91.000% |  |
| assets/ui/test/背包/长按提示 拷贝/bg_item 拷贝 2.png | candidate | 590×150 | 30×30 | 98.983% |  |
| assets/ui/test/背包/页面指示/页面指示 拷贝.png | skipped | 12×12 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/背包/页面指示/页面指示.png | skipped | 12×12 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/背景.png | candidate | 750×1624 | 10×10 | 99.992% |  |
| assets/ui/test/视频屏幕/750x1334.png | candidate | 750×1334 | 16×16 | 99.974% |  |
| assets/ui/test/视频屏幕/750x1624.png | candidate | 750×1624 | 84×86 | 99.407% |  |
| assets/ui/test/设置/bg_content/矩形 3 拷贝.png | candidate | 514×326 | 10×10 | 99.940% |  |
| assets/ui/test/设置/bg_win.png | candidate | 584×559 | 62×59 | 98.879% |  |
| assets/ui/test/设置/id/copy.png | skipped | 36×48 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/设置/lang/lang.png | skipped | 38×38 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/设置/lang/图层 15.png | skipped | 37×44 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/设置/progress_bar(bgm)/bg/矩形 41.png | candidate | 408×24 | 10×10 | 98.979% |  |
| assets/ui/test/设置/progress_bar(bgm)/bg/矩形 42.png | candidate | 398×34 | 10×10 | 99.261% |  |
| assets/ui/test/设置/progress_bar(bgm)/fill.png | candidate | 280×28 | 15×20 | 96.173% |  |
| assets/ui/test/设置/progress_bar(bgm)/矩形 44.png | candidate | 12×43 | 12×10 | 76.744% |  |
| assets/ui/test/设置/progress_bar(sfx)/bg/矩形 41.png | candidate | 407×24 | 10×10 | 98.976% |  |
| assets/ui/test/设置/progress_bar(sfx)/bg/矩形 42.png | candidate | 397×34 | 10×10 | 99.259% |  |
| assets/ui/test/设置/progress_bar(sfx)/fill.png | candidate | 312×28 | 15×20 | 96.566% |  |
| assets/ui/test/设置/server/server.png | skipped | 40×44 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/test/首次发现.提示/bg.png | candidate | 750×371 | 601×322 | 30.450% |  |
| assets/ui/test/首次发现.提示/矩形 1866.png | candidate | 853×175 | 10×10 | 99.933% |  |

## 视觉近似结果

这是允许像素变化的模式，不宣称逐像素无损。

| 图片 | 拉伸方式 | 平均误差 / 255 | 严重误差像素占比 |
|---|---|---|---|
| assets/ui/test/toasts/bg.png | nine_slice | 0.0000 | 0.0000% |
| assets/ui/test/任务/bg.png | nine_slice | 0.3119 | 0.1467% |
| assets/ui/test/任务/矩形 1266.png | nine_slice | 0.0000 | 0.0000% |
| assets/ui/test/任务/组 31/item/bg.png | nine_slice | 0.0092 | 0.1077% |
| assets/ui/test/任务/组 31/item/item/bg_item.png | nine_slice | 0.0000 | 0.0000% |
| assets/ui/test/任务/组 31/item/progress/progress_bar 拷贝/bg/矩形 42.png | nine_slice | 0.0000 | 0.0000% |
| assets/ui/test/任务/组 31/item/progress/progress_bar 拷贝/fill.png | horizontal_three_slice | 0.0000 | 0.0000% |
| assets/ui/test/任务/组 31/item 拷贝 10/claim/2.png | nine_slice | 0.0200 | 0.2359% |
| assets/ui/test/任务/组 31/item 拷贝 10/item/bg_item.png | nine_slice | 0.0000 | 0.0000% |
| assets/ui/test/任务/组 31/item 拷贝 7/bg.png | nine_slice | 0.0091 | 0.1068% |
| assets/ui/test/任务/组 31/item 拷贝 7/claim/2.png | nine_slice | 0.0200 | 0.2359% |
| assets/ui/test/任务/组 31/item 拷贝 7/progress/progress_bar 拷贝/fill/矩形 43 拷贝 2.png | horizontal_three_slice | 0.0000 | 0.0000% |
| assets/ui/test/任务/组 31/item 拷贝 7/progress/progress_bar 拷贝/fill/矩形 43.png | nine_slice | 0.0000 | 0.0000% |
| assets/ui/test/任务/组 31/item 拷贝 8/claim/2.png | nine_slice | 0.0200 | 0.2359% |
| assets/ui/test/任务/组 31/item 拷贝 8/progress/progress_bar 拷贝/bg/矩形 41.png | horizontal_three_slice | 0.0000 | 0.0000% |
| assets/ui/test/任务/组 31/item 拷贝 8/progress/progress_bar 拷贝/fill.png | horizontal_three_slice | 0.0000 | 0.0000% |
| assets/ui/test/任务/组 31/item 拷贝 9/claim/2.png | nine_slice | 0.0198 | 0.2329% |
| assets/ui/test/制造样式1/列表/组 29 拷贝 9/item/bed.png | nine_slice | 0.0000 | 0.0000% |
| assets/ui/test/制造样式1/材料预览/bg_item.png | nine_slice | 0.0000 | 0.0000% |
| assets/ui/test/制造样式1/配方/底板.png | nine_slice | 0.1277 | 0.1467% |
| assets/ui/test/制造样式2/确定取消 拷贝 2/item 拷贝 20/bg_item.png | nine_slice | 0.0000 | 0.0000% |
| assets/ui/test/制造样式2/确定取消 拷贝 2/no/矩形 1431 拷贝.png | nine_slice | 0.0000 | 0.0000% |
| assets/ui/test/场景/图层 1864.png | nine_slice | 0.1425 | 0.0000% |
| assets/ui/test/存储/bg.png | nine_slice | 0.1104 | 0.1274% |
| assets/ui/test/存储/箱子列表/grid/组 29 拷贝 3/item/bg_item.png | nine_slice | 0.0000 | 0.0000% |
| assets/ui/test/存储/背包.png | nine_slice | 0.0000 | 0.0000% |
| assets/ui/test/存储 拷贝/bg.png | nine_slice | 0.1104 | 0.1274% |
| assets/ui/test/对话样式1/build/1.png | nine_slice | 0.0056 | 0.0664% |
| assets/ui/test/对话样式1/destory/1.png | nine_slice | 0.0057 | 0.0672% |
| assets/ui/test/对话样式1/底部（对话）/build/2.png | nine_slice | 0.0075 | 0.0878% |
| assets/ui/test/底部（树木.砍伐）/bg_item.png | nine_slice | 0.0000 | 0.0000% |
| assets/ui/test/底部（树木.砍伐）/yes/矩形 18 拷贝 3.png | nine_slice | 0.0000 | 0.0000% |
| assets/ui/test/底部（流民.招募）/新手引导2 拷贝/toasts 拷贝 2/bg.png | nine_slice | 0.0000 | 0.0000% |
| assets/ui/test/底部（锁住的门）/materals/bg_item.png | nine_slice | 0.0000 | 0.0000% |
| assets/ui/test/建造列表/列表/组 29 拷贝 9/item/bg_item.png | nine_slice | 0.2842 | 0.2141% |
| assets/ui/test/建造列表/网格线/矩形 1428.png | nine_slice | 0.0683 | 0.1293% |
| assets/ui/test/建造列表/配方/底板.png | nine_slice | 0.1277 | 0.1467% |
| assets/ui/test/弹窗遮罩.png | nine_slice | 0.0000 | 0.0000% |
| assets/ui/test/恭喜获得/bg_恭喜获得.png | nine_slice | 0.2043 | 0.0000% |
| assets/ui/test/恭喜获得/item/bg_item.png | nine_slice | 0.0000 | 0.0000% |
| assets/ui/test/恭喜获得/弹窗遮罩 拷贝 2.png | nine_slice | 0.0000 | 0.0000% |
| assets/ui/test/战斗结束/胜/说明/组 34.png | nine_slice | 0.0129 | 0.0380% |
| assets/ui/test/抽卡/卡牌属性/frame.png | nine_slice | 0.0000 | 0.0000% |
| assets/ui/test/抽卡/图层 21.png | nine_slice | 0.0552 | 0.0221% |
| assets/ui/test/抽卡/弹窗遮罩 拷贝.png | nine_slice | 0.0000 | 0.0000% |
| assets/ui/test/抽卡/矩形 49.png | nine_slice | 0.0000 | 0.0000% |
| assets/ui/test/新手引导/toasts 拷贝/bg.png | nine_slice | 0.0000 | 0.0000% |
| assets/ui/test/新手引导/椭圆 776.png | nine_slice | 0.0000 | 0.0000% |
| assets/ui/test/新手引导/矩形 775.png | nine_slice | 0.0007 | 0.0023% |
| assets/ui/test/暂停/bg_content/矩形 3 拷贝.png | nine_slice | 0.0000 | 0.0000% |
| assets/ui/test/暂停/bg_win.png | nine_slice | 0.0000 | 0.0000% |
| assets/ui/test/暂停/exit/1.png | nine_slice | 0.0083 | 0.0981% |
| assets/ui/test/暂停/resume/2.png | nine_slice | 0.0084 | 0.0991% |
| assets/ui/test/暂停/title/bg 拷贝 2.png | nine_slice | 0.2552 | 0.0340% |
| assets/ui/test/组 36/组 35/图层 1884.png | nine_slice | 0.0014 | 0.0000% |
| assets/ui/test/组 36/组 35/矩形 1886.png | nine_slice | 0.0000 | 0.0000% |
| assets/ui/test/组件/progress_bar/bg/矩形 41.png | nine_slice | 0.0000 | 0.0000% |
| assets/ui/test/组件/progress_bar/bg/矩形 42.png | nine_slice | 0.0000 | 0.0000% |
| assets/ui/test/组件/progress_bar/fill.png | horizontal_three_slice | 0.0000 | 0.0000% |
| assets/ui/test/背包/组 28/add/add.png | nine_slice | 0.0000 | 0.0000% |
| assets/ui/test/背包/组 28/add/矩形 34 拷贝 2.png | nine_slice | 0.0000 | 0.0000% |
| assets/ui/test/背包/组 28/item_bg.png | nine_slice | 0.0000 | 0.0000% |
| assets/ui/test/背包/组 28/items/item/矩形 1188.png | nine_slice | 0.0000 | 0.0000% |
| assets/ui/test/背包/组 28/items/item 拷贝 5/矩形 1188.png | nine_slice | 0.0000 | 0.0000% |
| assets/ui/test/背包/选中框 拷贝.png | nine_slice | 0.0000 | 0.0000% |
| assets/ui/test/背包/长按提示 拷贝/bg_item 拷贝 2.png | nine_slice | 0.0000 | 0.0000% |
| assets/ui/test/背景.png | nine_slice | 0.0000 | 0.0000% |
| assets/ui/test/视频屏幕/750x1334.png | nine_slice | 0.0000 | 0.0000% |
| assets/ui/test/视频屏幕/750x1624.png | nine_slice | 0.0297 | 0.0296% |
| assets/ui/test/设置/bg_content/矩形 3 拷贝.png | nine_slice | 0.0000 | 0.0000% |
| assets/ui/test/设置/bg_win.png | nine_slice | 0.0000 | 0.0000% |
| assets/ui/test/设置/progress_bar(bgm)/bg/矩形 41.png | nine_slice | 0.0000 | 0.0000% |
| assets/ui/test/设置/progress_bar(bgm)/bg/矩形 42.png | nine_slice | 0.0000 | 0.0000% |
| assets/ui/test/设置/progress_bar(bgm)/fill.png | nine_slice | 0.0344 | 0.2551% |
| assets/ui/test/设置/progress_bar(bgm)/矩形 44.png | vertical_three_slice | 0.0000 | 0.0000% |
| assets/ui/test/设置/progress_bar(sfx)/bg/矩形 41.png | nine_slice | 0.0000 | 0.0000% |
| assets/ui/test/设置/progress_bar(sfx)/bg/矩形 42.png | nine_slice | 0.0000 | 0.0000% |
| assets/ui/test/设置/progress_bar(sfx)/fill.png | nine_slice | 0.0309 | 0.2289% |
| assets/ui/test/首次发现.提示/bg.png | nine_slice | 0.0302 | 0.0000% |
| assets/ui/test/首次发现.提示/矩形 1866.png | nine_slice | 0.0000 | 0.0000% |
