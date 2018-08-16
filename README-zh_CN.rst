============
PyGame-Pal
============

.. image:: https://img.shields.io/badge/license-GPLv3-red.svg
.. image:: https://img.shields.io/badge/language-python-blue.svg
.. image:: https://img.shields.io/badge/python-2%20%7C%203-lightblue.svg
.. image:: https://img.shields.io/badge/platform-windows%20%7C%20linux%20%7C%20osx-purple.svg

一个基于pygame的对中国经典角色扮演游戏—— `仙剑奇侠传 <https://zh.wikipedia.org/wiki/%E4%BB%99%E5%89%91%E5%A5%87%E4%BE%A0%E4%BC%A0/>`_ 的开源重新实现。它在很大程度上参考了仙剑研究文档(http://github.com/palxex/palresearch)，

sdlpal项目(http://github.com/sdlpal/sdlpal)，

以及 huangcd 所做的工作(http://github.com/huangcd/python-pal)。

支持CPython 2.6/2.7 以及 CPython 3.3以上 的版本(当然，更推荐使用python3)，在 Manjaro Linux 17.1 和 Windows 7 64bit 系统中测试通过。

基础依赖：
___________
	| pygame (基于 sdl 1.x)
	| six
	| chardet
	| configobj
	| attrs
	| wcwidth
	| wrapt
	| pyperclip
	| pyaudio (播放音效及rix音乐)
	| mido (播放midi)

Python2专有依赖：
______________________________
	| enum34
	| textwrap3
	| backports.functools_lru_cache
	| backports.functools_partialmethod

可选依赖：
______________________
	| pyopl (基于dosbox的opl合成器, 用来模拟播放opl音乐. 如果是python3版本, 请使用此分支: https://github.com/pygametoys/pyopl/tree/pyopl-py3)
	| pyav (基于ffmpeg, 播放win95版的avi视频)
	| ptpython (更智能的控制台)
	| psyco (只能用于python2.6及之前的32位版本，据说会有一丝丝的加速效果)

开发依赖：
_________________________
	| cython (编译c扩展版本yj1/yj2解压模块)

特性：
_________

    1. 多线程方式播放音效

    2. 把可交互的控制台内置于游戏，如下图

    .. image:: screenshot.png

    3. 一个简陋的gui设置工具

    如果说还有什么，那就是函数命名一律不得使用驼峰!还有修改代码后无需重编译也是很酷的，当然这些都是次要的

    很惭愧，只作了一点微小的工作

有待提升之处：
______________
    - 把一些残余的c语言风格的代码重构为python风格
    - 性能优化
    - 移植更多其它的opl模拟核心？
    - 测试手柄输入是否正常
    - 修复潜在bug.

协议：
________
    GPLv3
