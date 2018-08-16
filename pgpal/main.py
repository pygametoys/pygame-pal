#! /usr/bin/env python
# -*- coding: utf8 -*-
from .init import *
from . import script
from .pyconsole.pyconsole import Console
import time
import types

class MenuItem:

    def __init__(me, value, label, enabled, position):
        me.value = value
        me.label = label
        me.enabled = enabled
        me.pos = position

def iter_scrcap():
    for i in range(10000):
        if not os.path.exists('SCRN%s.bmp' % str(i).rjust(4, '0')):
            yield str(i).rjust(4, '0')

def run():
    game.cmdon = 1
    if game.cmdon:
        game.console = Console(game.screen,
                               (0, 0, 640, 300),
                               functions=dict((func.__name__, func) for func in script.commands.values()),
                               # {func.__name__:func for func in script.commands.values()},
                               key_calls={},
                               syntax={})
        game.console.setvar("active", 0)
    Class = None
    while game.state != 'exit':
        state = game.states[game.state]
        if game.cmdon: game.console.process_input()
        game.events = pg.event.get()
        if game.changed:
            gen = state()
        if isinstance(gen, types.GeneratorType):
            next(gen)
        else:
            gen()
        trans()
        if game.cmdon: game.console.draw()
        event_loop()
        pg.display.flip()
        game.changed = state != game.states[game.state]
    mp.exit()
    pg.quit()


def event_loop():
    for event in game.events:
        if event.type == ACTIVEEVENT:
            pass  # event.state in [2, 6] and event.gain
        elif event.type == QUIT:
            game.state = 'exit'
        elif event.type == VIDEORESIZE:
            if not game.FullScreen:
                game.SCREEN_SIZE = event.size
                game.screen = pg.display.set_mode(game.SCREEN_SIZE, HWSURFACE | DOUBLEBUF | RESIZABLE, 32)
        elif event.type == KEYDOWN:
            if event.mod & KMOD_ALT:
                if event.key == K_RETURN:
                    game.FullScreen = not game.FullScreen
                    if game.FullScreen:
                        game.screen = pg.display.set_mode(pg.display.list_modes()[0], HWSURFACE | DOUBLEBUF | FULLSCREEN, 32)
                    else:
                        game.screen = pg.display.set_mode(game.SCREEN_SIZE, HWSURFACE | DOUBLEBUF | RESIZABLE, 32)
                elif event.key == K_F4:
                    game.state = 'exit'
            elif event.mod & KMOD_CTRL and game.cmdon:
                if event.key == K_w:
                    game.console.set_active()
                elif event.key == K_q:
                    game.console.setvar("python_mode", not game.console.getvar("python_mode"))
                    game.console.set_interpreter()
            elif event.key == K_p:
                try:
                    fileno = next(iter_scrcap())
                    pg.image.save(game.screen, 'SCRN%s.bmp' % fileno)
                except StopIteration:
                    pass

def readMenu(items, labelColor, onchange=None):
    palette = Palettes.getPalette()
    render = lambda item, color, shadow: word.drawText(blit, item.label, item.pos, palette[color], shadow)
    color = labelColor
    for i, item in enumerate(items):
        if not item.enabled:
            if i == game.curItem: color = MENUITEM_COLOR_SELECTED_INACTIVE
            else: color = MENUITEM_COLOR_INACTIVE
        render(item,color, 1)
    if items[game.curItem].enabled:
        MENUITEM_COLOR_SELECTED = MENUITEM_COLOR_SELECTED_FIRST + (pg.time.get_ticks() // 100) % MENUITEM_COLOR_SELECTED_TOTALNUM
        render(items[game.curItem], MENUITEM_COLOR_SELECTED, 0)
    for event in game.events:
        if event.type == KEYDOWN:
            if event.key in [K_DOWN, K_RIGHT, K_UP, K_LEFT]:
                if items[game.curItem].enabled:
                    render(items[game.curItem], labelColor, 0)
                else:
                    render(items[game.curItem], MENUITEM_COLOR_INACTIVE, 0)
                if event.key in [K_DOWN, K_RIGHT]:
                    game.curItem = (game.curItem + 1) % len(items)
                else:
                    game.curItem = (game.curItem - 1) % len(items)
                if items[game.curItem].enabled:
                    render(items[game.curItem], MENUITEM_COLOR_SELECTED, 0)
                else:
                    render(items[game.curItem], MENUITEM_COLOR_SELECTED_ACTIVE, 0)
            elif event.key == K_ESCAPE:
                if items[game.curItem].enabled:
                    render(items[game.curItem], labelColor, 0)
                else:
                    render(items[game.curItem], MENUITEM_COLOR_INACTIVE, 0)
                return MENUITEM_VALUE_CANCELLED
            elif event.key in [K_RETURN, K_SPACE]:
                if items[game.curItem].enabled:
                    render(items[game.curItem], MENUITEM_COLOR_CONFIRMED, 0)
                    return items[game.curItem].value
    return None


def readSaveSlotMenu():
    pass


def trademark_screen():
    game.on = 0
    dismkf.curPalette = 4
    Rng.startVideo(6)
    Rng.getNextFrame()
    game.FADEIN_EVENT = pg.USEREVENT + 0
    game.FADEOUT_EVENT = pg.USEREVENT + 1
    pg.time.set_timer(game.FADEIN_EVENT, 800 // 4)
    quit = 0

    while game.state == 'logo':
        blit(Rng.getCurrentFrame(), (0, 0))
        for event in game.events:
            if event.type == game.FADEIN_EVENT:
                if Rng.hasNextFrame():
                    blit(Rng.getNextFrame(), (0, 0))
                else:
                    quit = 1
        if quit:
            pg.time.set_timer(game.FADEIN_EVENT, 0)
            game.on = 1
            Rng.finishCurrentVideo()
            game.state = 'fadeout'
            game.next = 'splash'
            pg.time.set_timer(game.FADEOUT_EVENT, 125)
        yield


class SplashScreen:
    
    class Crane(pg.sprite.Sprite):
        
        SpriteCrane = Mgo[SPRITENUM_SPLASH_CRANE]
        
        def __init__(me, x, y, frame):
            pg.sprite.Sprite.__init__(me)
            me.frame = frame
            me.image = me.SpriteCrane[frame]
            me.rect = me.image.get_rect()
            me.rect.topleft = x, y

        def update(me):
            if not me.groups()[0].pressed:
                me.frame = (me.frame + (me.groups()[0].iCraneFrame & 1)) % 8
                me.image = me.SpriteCrane[me.frame]
                me.rect.y += 1 if game.on > 1 and game.on & 1 else 0
                me.rect.x -= 1
                if me.rect.x < -me.rect.width: me.kill()
    
    def __init__(me):
        game.light = game.on = 200
        pg.time.set_timer(game.FADEIN_EVENT, 85)
        dismkf.curPalette = 2
        me.BitmapDown, me.BitmapUp = Fbp[BITMAPNUM_SPLASH_DOWN], Fbp[BITMAPNUM_SPLASH_UP]
        me.BitmapTitle = Mgo[SPRITENUM_SPLASH_TITLE][0]
        me.cranes = pg.sprite.RenderPlain(*[me.Crane(randrange(300, 600), randrange(0, 80), randrange(0, 8)) for _ in range(9)])
        me.cranes.pressed = False
        me.cranes.iCraneFrame = 0
        script.playMusic(NUM_RIX_TITLE)

    def __call__(me):
        if game.on: blit(me.BitmapDown, (0, 200 - game.on))
        blit(me.BitmapUp, (0, -game.on))
        me.cranes.draw(game.temp)
        if me.cranes.pressed:
            blit(me.BitmapTitle, (255, 10))
        else:
            blit(me.BitmapTitle.subsurface(0, 0, me.BitmapTitle.get_width(), max(me.BitmapTitle.get_height() - game.on, 0)), (255, 10))
        for event in game.events:
            if event.type == KEYDOWN:
                if event.key in [K_RETURN, K_SPACE, K_ESCAPE] and not me.cranes.pressed:
                    pg.time.set_timer(game.FADEIN_EVENT, 0)
                    pg.time.set_timer(game.FADEOUT_EVENT, 8)
                    me.cranes.pressed += 1
            elif event.type == game.FADEIN_EVENT:
                me.cranes.update()
                me.cranes.iCraneFrame += 1
                if game.light >= 1:
                    game.light -= 1
                    game.mask.fill((0, 0, 0, int(game.light * 1.27 + 1)))
                    game.on = game.light
            elif event.type == game.FADEOUT_EVENT:
                if game.light == 0:
                    if me.cranes.pressed <= 2:
                        me.cranes.pressed += 1
                        pg.time.set_timer(game.FADEOUT_EVENT, 500)
                    else:
                        mp.stop()
                        pg.time.set_timer(game.FADEOUT_EVENT, 63)
                        game.on = 1
                        game.next = 'mainmenu'
                        game.state = 'fadeout'
                else:
                    game.light -= 3 + game.light % 3
                game.mask.fill((0, 0, 0, int(game.light * 1.27)))
        blit(game.mask, (0, 0))


def fade_out():
    while game.state == 'fadeout':
        if game.on < 255:
            game.mask.fill((0, 0, 0, game.on))
            blit(game.mask, (0, 0))
        else:
            game.on = 256
            game.mask.fill((0, 0, 0, game.on - 1))
            blit(game.mask, (0, 0))
            game.state = game.next
            pg.time.set_timer(game.FADEOUT_EVENT, 0)
            yield
        for event in game.events:
            if event.type == game.FADEOUT_EVENT:
                game.on <<= 1
        yield


def opening_menu():
    game.on -= 1
    pg.time.set_timer(game.FADEIN_EVENT, 10)
    game.curItem = 0
    dismkf.curPalette = 0
    menuBack = Fbp[MAINMENU_BACKGROUND_FBPNUM]
    items = [MenuItem(0, Word[MAINMENU_LABEL_NEWGAME], True, (125, 95)),
             MenuItem(1, Word[MAINMENU_LABEL_LOADGAME], True, (125, 112))]
    script.playMusic(RIX_NUM_OPENINGMENU)

    while game.state == 'mainmenu':
        blit(menuBack, (0, 0))
        selected = readMenu(items, MENUITEM_COLOR)
        if selected == 0:
            game.on = 1
            ScrMgr.loadDefault()
            defaultGame()
            game.state = 'fadeout'
            game.next = 'main'
            pg.time.set_timer(game.FADEIN_EVENT, 0)
            pg.time.set_timer(game.FADEOUT_EVENT, 125)
            mp.stop()
            yield
        elif selected == 1:
            save = readSaveSlotMenu()
        if game.on:
            game.mask.fill((0, 0, 0, int(255 * game.on / 4.25) >> 6))
            blit(game.mask, (0, 0))
        for event in game.events:
            if event.type == game.FADEIN_EVENT:
                if game.on > 1:
                    game.on -= 4.25
                else:
                    pg.time.set_timer(game.FADEIN_EVENT, 0)
        yield


class Main():
    def __init__(me):
        game.scene = ScrMgr.scene(game.sceneId)
        command = ScrMgr.script(game.scene.enterScriptId)
        script.run(command)
        game.eventId = game.scene.startEventId
        game.scriptId = game.scene.enterScriptId + 1
        Map.load(game.scene.mapId)
        game.endEventId = ScrMgr.scene(game.sceneId + 1).startEventId
        me.group = pg.sprite.Group()
        
        """
        while game.scriptId < game.scene.enterScriptId + 20:
            scr = ScrMgr.script(game.scriptId)
            if scr[0] in script.commands:
                script.run(scr)
                print(scr)
                print(script.commands[scr[0]].__doc__)
            else:
                print(hex(scr[0]),' not implemented')
            game.scriptId += 1
        """
        
    def __call__(me):
        blit(Map.getArea(game.scene.mapId, game.viewport, 0), (0, 0))
        blit(Map.getArea(game.scene.mapId, game.viewport, 1), (0, 0))
        game.group.update()
        game.group.draw(game.temp)
        me.group.update()
        me.group.draw(game.temp)

        while game.trigger:
            command = ScrMgr.script(game.scriptId)
            script.run(command)
            # print(command)
            game.scriptId += 1
            for game.eventId in range(game.scene.startEventId, game.endEventId):
                event = ScrMgr.event(game.eventId)
                if abs(event.vanishTime) <= 1:
                    if event.state > 0 and event.trigScr >= 4:
                        if abs(game.viewport[0] - event.x) + abs(game.viewport[1] - event.y) * 2 <= (event.trigMode - 4) * 32:
                            # if event.frame
                            scr = ScrMgr.script(event.trigScr)
                            if script.commands.has_key(scr[0]):
                                script.run(scr)
                                # print(scr)
                            else:
                                print(hex(scr[0]),' not implemented')
                        elif event.state < 0:
                            event.state = abs(event.state)
            for game.eventId in range(game.scene.startEventId, game.endEventId):
                event = ScrMgr.event(game.eventId)
                if event.autoScr and event.state:
                    scr = ScrMgr.script(event.autoScr)
                    if script.commands.has_key(scr[0]):
                        script.auto_run(scr)
                        # print(scr)
                    else:
                        print(hex(scr[0]),' not implemented')
                else:
                    pass
                    #print(game.eventId, event.x, event.y)
                if event.roleId != 0 and event.state:
                    x = event.x - game.viewport[0]
                    y = event.y - game.viewport[1]
                    npc = roles.Actor(pos = (x, y))
                    npc.path = event.dir
                    npc.tileId = event.roleId
                    npc.load(event.frame)
                    me.group.add(npc)
        for event in game.events:
            if event.type == KEYDOWN:
                w, h  = game.viewport
                if event.key == K_UP:
                    h -= 8
                    w += 16
                elif event.key == K_DOWN:
                    h += 8
                    w -= 16
                elif event.key == K_LEFT:
                    h -= 8
                    w -= 16
                elif event.key == K_RIGHT:
                    h += 8
                    w += 16
                if w in range(32, 1712) and h in range(16, 1848):
                    game.viewport = w, h
                if event.key == K_PAGEUP:
                    if game.scene.mapId > 1:
                        game.scene.mapId -= 1 
                elif event.key == K_PAGEDOWN:
                    if game.scene.mapId < Map.count - 1:
                        game.scene.mapId += 1 
                    
def main():
    if sys.version_info[0] == 2 and struct.calcsize('P') == 4:
        try:
            import psyco
            psyco.full()
        except ImportError:
            print('fail to use psyco')
    game()
    game.states = {'logo': trademark_screen,
                   'fadeout': fade_out,
                   'splash': SplashScreen,
                   'mainmenu': opening_menu,
                   'main': Main,
                   'ending': None,
                   'exit': None}
    #"""
    game.on = 200
    #"""
    run()
