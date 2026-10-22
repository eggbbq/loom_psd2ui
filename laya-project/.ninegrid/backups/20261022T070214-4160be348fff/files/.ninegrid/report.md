# NineGrid 优化报告

节省率表示纹理像素面积，非文件大小或 DrawCall。

| 图片 | 状态 | 原始尺寸 | 优化尺寸 | 面积节省 | 原因 |
|---|---|---|---|---|---|
| assets/ui/商城_给程序/切的/图层 68.png | candidate | 575×172 | 335×82 | 72.224% |  |
| assets/ui/商城_给程序/切的/图层 986.png | skipped | 106×168 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/商城_给程序/切的/组 24/椭圆 7.png | skipped | 27×31 |  | 0.000% | no_visual_candidate_within_budget |
| assets/ui/商城_给程序/切的/组 24/组 23.png | candidate | 141×63 | 107×63 | 24.113% |  |
| assets/ui/商城_给程序/切的/组 37.png | candidate | 738×1078 | 738×592 | 45.083% |  |
| assets/ui/商城_给程序/切的/组 9.png | skipped | 115×114 |  | 0.000% | no_visual_candidate_within_budget |

## 视觉近似结果

这是允许像素变化的模式，不宣称逐像素无损。

| 图片 | 拉伸方式 | 平均误差 / 255 | 严重误差像素占比 |
|---|---|---|---|
| assets/ui/商城_给程序/切的/图层 68.png | nine_slice | 0.3064 | 0.2356% |
| assets/ui/商城_给程序/切的/组 24/组 23.png | horizontal_three_slice | 0.0945 | 0.1914% |
| assets/ui/商城_给程序/切的/组 37.png | vertical_three_slice | 0.1351 | 0.2958% |
