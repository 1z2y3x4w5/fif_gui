本项目使用python3.9.13版本开发，请自行安装python3.9.13
# 克隆项目到本地
```bash
git clone https://github.com/1z2y3x4w5/fif_gui
```

# 使用

## 录制音频
   录制10s左右的样品音频，并保存在draft文件夹中

## 创建虚拟环境：
```bash
python3 -m venv venv
```

## 创建虚拟环境成功后，进入虚拟环境：
```bash
source venv/bin/activate
```

## 使用pip安装项目依赖
```bash
pip install -r requirements.txt
```

## 安装虚拟麦克风软件，如：VoiceMeeter
### 启动VoiceMeeter并配置

## 运行项目（在运行项目前务必打开虚拟麦克风软件VoiceMeeter，否则无法录音）：
```bash
python src/main.py
```


# 代码结构
```
src
├── main.py             # 主程序
├── connector           # FiF客户端连接器
├── speaker             # 语音合成器抽象
├── tts                 # TTS模型
├── vmic                # 虚拟麦克风
├── draft               # 样品音频
└── tem                 # 临时音频  
```



# 引用
- [Aurorabili/fuckfi](https://github.com/Aurorabili/fuckfif)
- [microsoft/playwright](https://github.com/microsoft/playwright)
- [Edresson/YourTTS](https://github.com/Edresson/YourTTS)
- [coqui-ai/TTS](https://github.com/coqui-ai/TTS)
