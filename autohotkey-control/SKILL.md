---
name: autohotkey-control
description: "通过本地已部署的 AutoHotkey v2 快速操作 Windows 桌面 GUI，包括启动软件、模拟鼠标点击/移动/拖拽、模拟键盘输入/快捷键、窗口激活/移动/调整大小/关闭、自动化安装向导和软件内设置。当用户要求打开软件、操作桌面应用、点击按钮、输入文字、按快捷键、操作窗口、自动化安装或任何需要桌面 GUI 交互的任务时使用本 Skill。优先于 computer-use（截图点击方式），因为 AutoHotkey 直接调用系统 API，速度更快、坐标更精准。"
---

# AutoHotkey 桌面控制

本地已部署 AutoHotkey v2.0.27 便携版，通过编写 AHK 脚本并执行来操作 Windows 桌面。

## 环境信息

- **可执行文件：** `C:\Tools\AutoHotkey\AutoHotkey64.exe`
- **版本：** v2.0.27
- **已加入系统 PATH**（当前会话可能需手动追加）
- **屏幕分辨率：** 1920×1080（坐标基于此）

## 核心工作流

1. 编写 AHK v2 脚本内容（使用 here-string）
2. 写入临时 `.ahk` 文件到 `$env:TEMP`
3. 用 `Start-Process` 调用 `AutoHotkey64.exe` 执行脚本
4. 如需等待结果，用 `-Wait` 参数；脚本内需将结果写入文件再回读

## 执行模板

```powershell
$script = @'
#Requires AutoHotkey v2.0
; 在这里写 AHK 代码
'@
$ahkPath = "$env:TEMP\ahk_task_$(Get-Random).ahk"
$script | Out-File -FilePath $ahkPath -Encoding utf8
Start-Process -FilePath "C:\Tools\AutoHotkey\AutoHotkey64.exe" -ArgumentList "`"$ahkPath`"" -Wait
```

如需脚本返回结果，在 AHK 中用 `FileAppend` 写入文件，执行后用 `Get-Content` 读取。

## 常用操作速查

### 启动程序
```ahk
Run "C:\path\to\program.exe"
Run "notepad.exe"
```

### 窗口操作
```ahk
WinActivate "窗口标题"          ; 激活窗口
WinWait "窗口标题",, 10          ; 等待窗口出现（最多10秒）
WinClose "窗口标题"               ; 关闭窗口
WinMove 100, 100, 800, 600, "标题"  ; 移动+调整大小
WinGetTitle(hwnd)                 ; 获取窗口标题
```

### 鼠标操作
```ahk
Click 500, 300                    ; 点击指定坐标
Click 500, 300, 2                 ; 双击
MouseMove 500, 300, 10            ; 移动鼠标（速度10，0=最快）
MouseClick "right", 500, 300      ; 右键点击
MouseClickDrag "left", 100, 100, 500, 500  ; 拖拽
MouseGetPos(&x, &y)               ; 获取当前鼠标位置
```

### 键盘操作
```ahk
Send "Hello World"                 ; 输入文字
Send "^c"                          ; Ctrl+C（^=Ctrl, !=Alt, +=Shift, #=Win）
Send "{Enter}"                     ; 回车键
Send "{Tab}"                       ; Tab键
Send "{F5}"                        ; F5功能键
Send "{Down 3}"                    ; 按3次下箭头
Sleep 1000                         ; 等待1000毫秒
```

### 控件/图像查找（复杂界面）
```ahk
; 等待特定文字出现（通过窗口标题或控件）
ControlClick "Button1", "窗口标题"  ; 点击指定控件
; 图像查找需提前准备截图，用 ImageSearch
```

## 坐标系统

- AutoHotkey 使用屏幕绝对坐标，原点 (0,0) 在屏幕左上角
- 当前分辨率 1920×1080，x 范围 0-1919，y 范围 0-1079
- 如需获取控件精确坐标，先用 `MouseGetPos` 在目标位置悬停获取

## 安全边界

以下操作必须在执行前请求用户确认或接管：
- 登录、验证码、支付密码
- UAC 提权弹窗
- 永久删除文件、格式化
- 不可逆的提交操作
- 修改系统关键设置

## 与 computer-use 的选择

- **优先用本 Skill（AutoHotkey）**：已知程序路径、已知窗口标题、已知坐标、重复性操作
- **用 computer-use**：未知界面、需要视觉识别、复杂安装向导中不确定下一步按钮位置、AutoHotkey 无法处理的场景

## 重要语法注意

- **AHK v2 中分号 `;` 是注释符，不是语句分隔符**，多条语句必须换行写，不能用 `;` 连在一行
- 用 `Invoke-Ahk.ps1 -Code` 传参时，脚本会自动把 `;` 转为换行；但若字符串字面量中含分号，请直接写完整 `.ahk` 文件

## 调试技巧

- 脚本开头加 `#Requires AutoHotkey v2.0` 确保版本正确
- 用 `MsgBox "调试信息"` 弹出提示检查执行位置
- 用 `FileAppend` 将变量写入日志文件
- 坐标不确定时，先写脚本获取鼠标位置：`MouseGetPos(&x,&y); FileAppend x "," y, A_Temp "\pos.txt"`
