# coding: utf-8
import mido
from wcwidth import wcswidth
from pgpal.compat import pg, textwrap, unicode_literals
from pgpal.configpage import pyform
from pgpal.const import *
from pgpal import configspec, config, vdt

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
    pg.init()
    pg.display.set_caption('Pygame-Pal config')
    screen = pg.display.set_mode((960, 40 * (len(configspec) + 2)), pg.RESIZABLE)
    screen.fill((255, 255, 255))

    # returns a function that prints the value of the given form
    # used for on_change
    def validate(this):
        def ret():
            new_cfg = this.value
            old_cfg = config.copy()
            config.update(new_cfg)
            if config.validate(vdt) is not True:
                config.update(old_cfg)
        return ret

    # allows repeats when holding down a key
    pyform.set_key_repeat(True)
    form = pyform.Form("main")

    label = pyform.Label('notice:', u'按回车键保存配置, esc退出', pos=(10, 10), text_color=(255, 0, 0))
    form.add_form_object(label)
    for i, (key, spec) in enumerate(configspec.items()):
        row = 50 + i * 40
        col = 10
        name = translate(key) + ':'
        label = pyform.Label(name, name, pos=(col, row), text_color=(120, 20, 120))
        form.add_form_object(label)
        col += wcswidth(name) * 20
        fun_name, fun_args, fun_kwargs, default = vdt._parse_with_caching(spec)
        current = str(config[key])
        if key == 'midi_port':
            fun_name = 'option'
            fun_args = mido.get_output_names()
        if fun_name == 'integer':
            form.add_form_object(pyform.TextInput(key, pos=(col, row), input_width=400,
                                 default_text='-'.join(fun_args), default=current, allowed_chars=pyform.TextInput.NUMS))
        elif fun_name == 'string':
            form.add_form_object(pyform.TextInput(key, pos=(col, row), input_width=400,
                                 default_text=translate(key), default=current))
        elif fun_name == 'boolean':
            radiogroup = pyform.RadioGroup(key, bool(config[key]))
            radiogroup.add_button(pyform.RadioButton("False", u'否', pos=(col, row), text_color=(120, 20, 120)))
            radiogroup.add_button(pyform.RadioButton("True", u'是', pos=(col + 120, row), text_color=(120, 20, 120)))
            form.add_form_object(radiogroup)
        elif fun_name == 'option':
            radiogroup = pyform.RadioGroup(key, fun_args.index(current) if current in fun_args else 0)
            for option in fun_args:
                btn = pyform.RadioButton(option, textwrap.shorten(option, width=15), pos=(col, row), text_color=(120, 20, 120))
                radiogroup.add_button(btn)
                col += btn._label_focus_area.w + 40
            form.add_form_object(radiogroup)

    form.on_change = validate(form)
    # create the pg clock
    clock = pg.time.Clock()

    while True:
        clock.tick(30)

        # events for the inputs
        events = pg.event.get()

        # process other events
        for event in events:
            if event.type == QUIT:
                return
            if event.type == pg.VIDEORESIZE:
                screen = pg.display.set_mode(event.size, pg.RESIZABLE)
            if event.type == KEYDOWN:
                if event.key == K_RETURN:
                    config.write()
                elif event.key == K_ESCAPE:
                    return

        screen.fill((255, 255, 255))

        # update the form
        form.update(events)
        form.draw(screen)

        pg.display.flip()


if __name__ == '__main__':
    main()
