# loopbench-sim-mujoco

Gymnasium 环境 `Loopbench/MuJoCo-Tabletop-v0`。任务 id 与 `loopbench-spec` 相同，几何用米，接触和重力由 MuJoCo 积分。

因素仍是名字。这个包自己决定 `friction=low` 是滑动摩擦 0.08，`camera=shifted` 是头顶相机平移 `(0.06, -0.045)`，`lighting=dim` 把光源 diffuse 乘 0.45。

夹爪是 mocap。闭合且对准物体时按相对位姿跟随，松开后物体重新受重力和摩擦支配。推动任务打开夹爪碰撞，让冰球被接触推进区域。
