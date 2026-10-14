# ADR 0003：真值默认不进 info

## 状态

接受。

## 背景

oracle 需要物体位姿才能当上界。视觉策略如果也能读到同一份 info，评测就不再是在测感知。标定又确实需要一小段带位姿的图像，否则颜色原型无法补光照。

## 决定

环境只有在 `expose_privileged=True` 时才把 `privileged` 放进 info。评测器只在 `policy.needs_privileged` 为真时这样创建环境，并用 `public_info` 再滤一次。

`improve()` 可以自己 `make_env(expose_privileged=True)` 做标定。它返回的策略在下一轮里重新走普通评测，不再看到真值。

## 后果

界面上 oracle 的记录会标明 privileged。视觉策略的闭环分数可以和 oracle 比，但不会偷偷用同一份答案。标定数据的采集和得分是两条记录。
