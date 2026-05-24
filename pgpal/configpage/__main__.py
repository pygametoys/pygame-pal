# coding: utf-8
import mido
from pgpal import configspec, config, initialize_runtime, vdt

import FreeSimpleGUI as sg

mido.set_backend('mido.backends.pygame')


translations = {
    'path': '目录',
    'volume': '音量',
    'chip': '芯片',
    'full': '全',
    'screen': '屏',
    'use': '使用',
    'font': '字体',
    'file': '文件',
    'samplerate': '采样率',
    'window': '窗口',
    'music': '音乐',
    'game': '游戏',
    'enable': '启用',
    'port': '端口',
    'backend': '后端',
    'width': '宽度',
    'height': '高度',
    'sound': '音效',
    'type': '类型',
    'mouse': '鼠标',
    'joystick': '手柄',
    'play': '播放',
    'embedded': '嵌入',
    'msg': '语言',
    'battle': '战斗',
    'fps': '帧率',
    'show': '显示',
    'console': '控制台'
}

def translate(key):
    return ''.join(translations.get(word, word.capitalize()) for word in key.split('_'))

def main():
    initialize_runtime()
    layout = []
    int_keys = []
    for key, spec in configspec.items():
        name = translate(key) + ':'
        fun_name, fun_args, fun_kwargs, default = vdt._parse_with_caching(spec)
        current = config[key]
        if key == 'midi_port':
            fun_name = 'option'
            fun_args = mido.get_output_names()
        line = [
            sg.Text(name, size=(10, 1))
        ]
        if fun_name == "option":
            line.append(
                sg.InputCombo(
                    values=fun_args,
                    default_value=current,
                    key=key
                )
            )
            layout.append(line)
        elif fun_name == 'string':
            line.append(
                sg.InputText(
                    default_text=current,
                    key=key
                )
            )
            layout.append(line)
        elif fun_name == 'integer':
            line.append(
                sg.InputText(
                    default_text=current,
                    enable_events=True,
                    key=key,
                )
            )
            layout.append(line)
            int_keys.append(key)
        elif fun_name == 'boolean':
            line.append(
                sg.Checkbox(
                    text='',
                    default=current,
                    key=key
                )
            )
            layout.append(line)

    layout.append(
        [sg.Button('确定'), sg.Button('取消')]
    )

    window = sg.Window('Pygame-Pal config', layout)

    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, '取消'):
            break
        if event == '确定':
            new_cfg = values
            old_cfg = config.copy()
            config.update(new_cfg)
            if config.validate(vdt) is not True:
                config.update(old_cfg)
            else:
                config.write()
            break
        elif event in int_keys and values[event]:
            try:
                int(values[event])
            except Exception:
                window[event].update(values[event][:-1])
    window.close()


if __name__ == '__main__':
    main()
