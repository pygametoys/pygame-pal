# -*- coding: utf8 -*-
from pgpal.compat import pg, range
from pgpal.const import *
from pgpal.mkfext import MAP
from pgpal.player import Sprite
from pgpal.utils import Structure, pal_x, pal_y, static_vars


class Scene(Structure):
    _fields_ = [
        ('H', 'map_num'),
        ('H', 'script_on_enter'),
        ('H', 'script_on_teleport'),
        ('H', 'event_object_index')
    ]


class SceneLoaderMixin(object):
    def __init__(self):
        self.viewport = 0, 0
        self.maps = MAP()
        self.sprite_to_draw = pg.sprite.OrderedUpdates()

    def add_sprite_to_draw(self, sprite_frame, pos, layer):
        assert len(self.sprite_to_draw) < MAX_SPRITE_TO_DRAW
        self.sprite_to_draw.add(Sprite(sprite_frame, pos, layer))

    def calc_cover_tiles(self, sprite):
        sx = pal_x(self.viewport) + pal_x(sprite.pos)
        sy = pal_y(self.viewport) + pal_y(sprite.pos)
        sh = bool(sx % 32)
        width, height = sprite.frame.size
        dx = dy = dh = 0
        for y in range((sy - height - 15) // 16, sy // 16 + 1):
            for x in range(
                (sx - width // 2) // 32,
                (sx + width // 2) // 32 + 1
            ):
                for i in range(
                    0 if x == (sx - width // 2) // 32 else 3, 5
                ):
                    if i == 0:
                        dx, dy, dh = x, y, sh
                    elif i == 1:
                        dx = x - 1
                    elif i == 2:
                        dx = x if sh else x - 1
                        dy = y + 1 if sh else y
                        dh = 1 - sh
                    elif i == 3:
                        dx, dy, dh = x + 1, y, sh
                    elif i == 4:
                        dx = x + 1 if sh else x
                        dy = y + 1 if sh else y
                        dh = 1 - sh
                    for l in range(2):
                        tile = self.maps.get_tile_bitmap(dx, dy, dh, l)
                        tile_hight = self.maps.get_tile_height(dx, dy, dh, l)
                        if tile is not None and tile_hight > 0 and (
                            (dy + tile_hight) * 16 + dh * 8 >= sy
                        ):
                            self.add_sprite_to_draw(
                                tile,
                                (
                                    dx * 32 + dh * 16 - 16 - pal_x(self.viewport),
                                    dy * 16 + dh * 8 + 7 + l + (
                                        tile_hight * 8
                                    ) - pal_y(self.viewport)
                                ),
                                tile_hight * 8 + l
                            )

    def npc_walk_one_step(self, event_object_id, speed):
        if event_object_id == 0 or event_object_id > len(self.event_objects):
            return
        p = self.event_objects[event_object_id - 1]
        p.x += (-2 if p.direction in {Direction.West,
                                      Direction.South} else 2) * speed
        p.y += (-1 if p.direction in {Direction.West,
                                      Direction.North} else 1) * speed
        if p.sprite_frames_num > 0:
            p.current_frame_num += 1
            p.current_frame_num %= (
                4 if p.sprite_frames_num == 3 else p.sprite_frames_num
            )
        elif p.sprite_frames_auto > 0:
            p.current_frame_num += 1
            p.current_frame_num %= (p.sprite_frames_auto)

    @static_vars(index=0)
    def apply_wave(self, surface):
        save = self.apply_wave.__dict__
        wave = [0] * 32
        self.screen_wave += self.wave_progression
        self.screen_wave &= 0xFFFF
        if self.screen_wave == 0 or self.screen_wave >= 256:
            self.screen_wave = self.wave_progression = 0
            return
        a = 0
        b = 60 + 8
        for i in range(16):
            b -= 8
            a += b
            wave[i] = a * self.screen_wave // 256
            wave[i + 16] = 320 - wave[i]
        a = save['index']
        pxarray = pg.PixelArray(surface)
        for p in range(200):
            b = wave[a]
            if b > 0:
                pxarray[:320 - b, p], pxarray[320 - b:320, p] = pxarray[b:320, p], pxarray[:b, p]
            a = (a + 1) % 32
        save['index'] = (save['index'] + 1) % 32
        del pxarray
        surface.unlock()

    def scene_draw_sprites(self):
        self.sprite_to_draw.empty()
        for i in range(self.max_party_member_index + self.follower_num + 1):
            if i > MAX_PLAYERS_IN_PARTY:
                break
            sprite = self.player_sprites[i]
            if sprite is None:
                continue
            sprite_frame = sprite[self.party[i].frame]
            if sprite_frame is None:
                continue
            self.add_sprite_to_draw(
                sprite_frame,
                (
                    self.party[i].x - sprite_frame.width // 2,
                    self.party[i].y + self.layer + 10
                ),
                self.layer + 6
            )
            self.calc_cover_tiles(self.sprite_to_draw.sprites()[-1])
        for i in range(
            self.scenes[self.num_scene - 1].event_object_index,
            self.scenes[self.num_scene].event_object_index,
        ):
            evt_obj = self.event_objects[i]
            if evt_obj.state == ObjectState.Hidden:
                continue
            elif evt_obj.vanish_time > 0:
                continue
            elif evt_obj.state < 0:
                continue
            sprite = self.get_event_object_sprite((i & 0xFFFF) + 1)
            if sprite is None:
                continue
            frame = evt_obj.current_frame_num
            if evt_obj.sprite_frames_num == 3:
                if frame == 2:
                    frame = 0
                elif frame == 3:
                    frame = 2
            sprite_frame = sprite[
                evt_obj.direction * evt_obj.sprite_frames_num + frame
            ]
            if sprite_frame is None:
                continue
            x = evt_obj.x - pal_x(self.viewport)
            x -= sprite_frame.width // 2
            if x >= 320 or x < -sprite_frame.width:
                continue
            y = evt_obj.y - pal_y(self.viewport)
            y += evt_obj.layer * 8 + 9
            vy = y - sprite_frame.height - evt_obj.layer * 8 + 2
            if vy >= 200 or vy < -sprite_frame.height:
                continue
            self.add_sprite_to_draw(
                sprite_frame,
                (x, y),
                evt_obj.layer * 8 + 2
            )
            self.calc_cover_tiles(self.sprite_to_draw.sprites()[-1])
        self.sprite_to_draw._spritelist.sort(key=lambda sprite: pal_y(sprite.pos))
        for p in self.sprite_to_draw:
            x = pal_x(p.pos)
            y = pal_y(p.pos) - p.frame.height - p.layer
            p.frame.blit_to(self.screen, (x, y))

    def check_obstacle(self, pos, check_event_objects, self_object):
        x, y = pos
        if not pg.Rect(0, 0, 2047, 2047).collidepoint(x, y):
            return True
        x, xr = divmod(x, 32)
        y, yr = divmod(y, 16)
        h = 0
        if xr + yr * 2 >= 16:
            if xr + yr * 2 >= 48:
                x += 1
                y += 1
            elif 32 - xr + yr * 2 < 16:
                x += 1
            elif 32 - xr + yr * 2 < 48:
                h = 1
            else:
                y += 1
        if self.maps.tile_blocked(x, y, h):
            return True
        if check_event_objects:
            for i in range(
                self.scenes[self.num_scene - 1].event_object_index,
                self.scenes[self.num_scene].event_object_index,
            ):
                p = self.event_objects[i]
                if i == self_object - 1:
                    continue
                if p.state >= ObjectState.Blocker:
                    if abs(p.x - pal_x(pos)) + abs(p.y - pal_y(pos)) * 2 < 16:
                        return True
        return False

    def make_scene(self):
        rect = pg.Rect(self.viewport, (320, 200))
        self.maps.blit_to(self.screen, rect, 0)
        self.maps.blit_to(self.screen, rect, 1)
        self.apply_wave(self.screen)
        self.scene_draw_sprites()
        if self.need_fadein:
            self.update_screen()
            self.fadein(1)
            self.need_fadein = False

    def update_party(self):
        if self.input_state.curdir != Direction.Unknown:
            x_offset = -16 if self.input_state.curdir in {
                Direction.West, Direction.South} else 16
            y_offset = -8 if self.input_state.curdir in {
                Direction.West, Direction.North} else 8
            x_source = pal_x(self.viewport) + pal_x(self.partyoffset)
            y_source = pal_y(self.viewport) + pal_y(self.partyoffset)
            x_target = x_source + x_offset
            y_target = y_source + y_offset
            self.party_direction = self.input_state.curdir
            if not self.check_obstacle((x_target, y_target), True, 0):
                for i in range(4, 0, -1):
                    self.trail[i] = self.trail[i - 1]
                self.trail[0].direction = self.input_state.curdir
                self.trail[0].x = x_source
                self.trail[0].y = y_source
                self.viewport = (
                    pal_x(self.viewport) + x_offset,
                    pal_y(self.viewport) + y_offset
                )
                self.update_party_gestures(True)
                return
        self.update_party_gestures(False)

    @static_vars(this_step_frame=0)
    def update_party_gestures(self, walking):
        save = self.update_party_gestures.__dict__
        step_frame_follower = step_frame_leader = 0
        if walking:
            save['this_step_frame'] = (save['this_step_frame'] + 1) % 4
            if save['this_step_frame'] & 1:
                step_frame_leader = (save['this_step_frame'] + 1) // 2
                step_frame_follower = 3 - step_frame_leader
            else:
                step_frame_leader = step_frame_follower = 0
            self.party[0].x = pal_x(self.partyoffset)
            self.party[0].y = pal_y(self.partyoffset)
            if self.player_roles.walk_frames[self.party[0].player_role] == 4:
                self.party[0].frame = self.party_direction * 4 + save['this_step_frame']
            else:
                self.party[0].frame = self.party_direction * 3 + step_frame_leader
            for i in range(1, self.max_party_member_index + 1):
                self.party[i].x = self.trail[1].x - pal_x(self.viewport)
                self.party[i].y = self.trail[1].y - pal_y(self.viewport)
                if i == 2:
                    self.party[i].x += -16 if self.trail[1].direction in {Direction.East, Direction.West} else 16
                    self.party[i].y += 8
                else:
                    self.party[i].x += 16 if self.trail[1].direction in {
                        Direction.West, Direction.South} else -16
                    self.party[i].y += 8 if self.trail[1].direction in {
                        Direction.West, Direction.North} else -8
                if self.check_obstacle((
                    self.party[i].x + pal_x(self.viewport),
                    self.party[i].y + pal_y(self.viewport)
                ), True, 0):
                    self.party[i].x = self.trail[1].x - pal_x(self.viewport)
                    self.party[i].y = self.trail[1].y - pal_y(self.viewport)
                if self.player_roles.walk_frames[self.party[i].player_role] == 4:
                    self.party[i].frame = self.trail[2].direction * \
                                          4 + save['this_step_frame']
                else:
                    self.party[i].frame = self.trail[2].direction * \
                                          3 + step_frame_leader
            if self.follower_num > 0:
                self.party[self.max_party_member_index + 1].x = self.trail[3].x - pal_x(self.viewport)
                self.party[self.max_party_member_index + 1].y = self.trail[3].y - pal_y(self.viewport)
                self.party[self.max_party_member_index + 1].frame = (
                    self.trail[3].direction * 3 + step_frame_follower
                )
        else:
            i = self.player_roles.walk_frames[self.party[0].player_role] or 3
            self.party[0].frame = self.party_direction * i
            for i in range(self.max_party_member_index):
                f = self.player_roles.walk_frames[self.party[i + 1].player_role] or 3
                self.party[i + 1].frame = self.trail[2].direction * f
            if self.follower_num > 0:
                self.party[self.max_party_member_index + 1].frame = self.trail[3].direction * 3
            save['this_step_frame'] &= 2
            save['this_step_frame'] ^= 2
