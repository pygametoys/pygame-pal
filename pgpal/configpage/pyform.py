# modified from https://github.com/Iluvatar/pyform
from pygame.locals import *
import pygame
import pyperclip


def get_default_font():
    all_fonts = pygame.font.get_fonts()
    return max(
        all_fonts,
        key=lambda fontname: fontname.count('sim') + fontname.count('cjk')
    )


def set_key_repeat(p):
    if p:
        pygame.key.set_repeat(150, 30)
    else:
        pygame.key.set_repeat()


class InputObject(object):
    @property
    def value(self):
        raise NotImplementedError("Not implemented")

    def draw(self, surface):
        raise NotImplementedError("Not implemented")

    def update(self, events):
        raise NotImplementedError("Not implemented")


class Label(InputObject):
    def __init__(self, name, text, pos=(0, 0), text_color=(0, 0, 0), font=None):
        self.name = name
        self.text = text
        self.pos = pos
        self.text_color = text_color
        if font is None:
            self.font = pygame.font.SysFont(get_default_font(), 24)
        else:
            self.font = font

    @property
    def value(self):
        return self.text

    def update(self, events):
        pass

    def draw(self, surface):
        rendered_text = self.font.render(self.text, 1, self.text_color)
        surface.blit(rendered_text, self.pos)


class TextInput(InputObject):
    """
    A text input for pygame apps

    Constructor option                      Default arg
    ------------------                      -----------
    position on screen                      pos=(0, 0)    # (x, y)
    text color                              text_color=(0, 0, 0)    # (r, g, b)
    input box width                         input_width=100
    max string length (negative unlimited)  max_length=-1
    set of allowed characters               allowed_chars=ALL_CHARS
    input prompt                            prompt=""
    default text                            default_text=""
    font                                    font=None

    Public properties
        reference name:     inputObj.name
        locked input:       inputObj.locked
        position:           inputObj.pos OR inputObj.x OR inputObj.y
        user input:         inputObj.text
        on change function: inputObj.on_change

    To use, call update() with all pygame events, then draw() with the pygame surface to draw to

        inputObj.update(events)
        inputObj.draw(surface)

    Other notes:
        clicking the input selects it, clicking outside it deselects it
        locked inputs cannot be selected or changed
        opt+backspace deletes the last word
        cmd/ctrl+backspace deletes the whole line

    """

    unshifted_keys = {K_a: 'a', K_b: 'b', K_c: 'c', K_d: 'd', K_e: 'e', K_f: 'f', K_g: 'g', K_h: 'h', K_i: 'i',
                      K_j: 'j', K_k: 'k', K_l: 'l', K_m: 'm', K_n: 'n', K_o: 'o', K_p: 'p', K_q: 'q', K_r: 'r',
                      K_s: 's', K_t: 't', K_u: 'u', K_v: 'v', K_w: 'w', K_x: 'x', K_y: 'y', K_z: 'z', K_0: '0',
                      K_1: '1', K_2: '2', K_3: '3', K_4: '4', K_5: '5', K_6: '6', K_7: '7', K_8: '8', K_9: '9',
                      K_BACKQUOTE: '`', K_MINUS: '-', K_EQUALS: '=', K_LEFTBRACKET: '[', K_RIGHTBRACKET: ']',
                      K_BACKSLASH: '\\', K_SEMICOLON: ';', K_QUOTE: '\'', K_COMMA: ',', K_PERIOD: '.', K_SLASH: '/',
                      K_SPACE: ' '}

    shifted_keys = {K_a: 'A', K_b: 'B', K_c: 'C', K_d: 'D', K_e: 'E', K_f: 'F', K_g: 'G', K_h: 'H', K_i: 'I', K_j: 'J',
                    K_k: 'K', K_l: 'L', K_m: 'M', K_n: 'N', K_o: 'O', K_p: 'P', K_q: 'Q', K_r: 'R', K_s: 'S', K_t: 'T',
                    K_u: 'U', K_v: 'V', K_w: 'W', K_x: 'X', K_y: 'Y', K_z: 'Z', K_0: ')', K_1: '!', K_2: '@', K_3: '#',
                    K_4: '$', K_5: '%', K_6: '^', K_7: '&', K_8: '*', K_9: '(', K_BACKQUOTE: '~', K_MINUS: '_',
                    K_EQUALS: '+', K_LEFTBRACKET: '{', K_RIGHTBRACKET: '}', K_BACKSLASH: '|', K_SEMICOLON: ':',
                    K_QUOTE: '"', K_COMMA: '<', K_PERIOD: '>', K_SLASH: '?', K_SPACE: ' '}

    ALPHA = " abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_"
    NUMS = "0123456789"
    SPECIAL = "!\"#$%&\\'()*+,-./:;<=>?@[\]^`{|}~"
    ALPHA_NUMS = ALPHA + NUMS
    ALL_CHARS = ALPHA + NUMS + SPECIAL

    def __init__(self, name, pos=(0, 0), text_color=(0, 0, 0), input_width=100, max_length=-1, allowed_chars=ALL_CHARS,
                 prompt="", default_text="", on_change=None, font=None, default=''):

        pygame.init()

        self.name = name
        self._pos = pos
        self.text_color = text_color
        self.input_width = input_width
        self.max_length = max_length
        self.allowed_chars = set(allowed_chars)
        self._prompt = prompt
        self.default_text = default_text
        self.on_change = on_change
        if font is None:
            self.font = pygame.font.SysFont(get_default_font(), 24)
        else:
            self.font = font

        self._rendered_prompt = self.font.render(self._prompt, 1, self.text_color)
        self._prompt_size = self._rendered_prompt.get_size()
        self._input_pad = self.font.render(' ', 1, self.text_color).get_width() // 2
        self._input_box = None
        self._focus_area = None
        self._recalculate_boxes()

        self.focused = False
        self._text = default
        self.shifted = 0
        self.alt = 0
        self.meta = 0
        self._locked = False

    # getters and setters for position

    @property
    def x(self):
        return self._pos[0]

    @property
    def y(self):
        return self._pos[1]

    @property
    def pos(self):
        return self._pos

    @pos.setter
    def pos(self, value):
        self._pos = value
        self._recalculate_boxes()

    def _recalculate_boxes(self):
        """ recalculate the bounding boxes once the position is changed """

        self._input_box = pygame.Rect(self.x + self._prompt_size[0], self.y, self.input_width + self._input_pad * 2,
                                      self._prompt_size[1])
        self._focus_area = pygame.Rect(self.x, self.y, self.input_width + self._input_pad * 2 + self._prompt_size[0],
                                       self._prompt_size[1])

    # getter and setter for locked property

    @property
    def locked(self):
        return self._locked

    @locked.setter
    def locked(self, value):
        self._locked = value
        if self._locked:
            self.focused = False

    def toggle_lock(self):
        """ convenience method for switching the lock state """

        self.locked = not self.locked

    # getter and setter for value property

    @property
    def value(self):
        return self._text

    @value.setter
    def value(self, value):
        if self._text == value:
            return

        if type(value) is not str:
            return

        self._text = value

        try:
            self.on_change()
        except TypeError:
            pass

    def draw(self, surface):
        """ draw the input box on the given surface """

        surface.blit(self._rendered_prompt, (self.x, self.y))

        # background
        if not self.locked:
            pygame.draw.rect(surface, (252, 252, 252), self._input_box)
        else:
            pygame.draw.rect(surface, (235, 235, 235), self._input_box)

        if self.focused:
            pygame.draw.rect(surface, (58, 117, 255), self._input_box, 1)
        else:
            pygame.draw.rect(surface, (208, 208, 208), self._input_box, 1)
            pygame.draw.line(surface, (169, 169, 169), (self.x + self._prompt_size[0], self.y),
                             (self.x + self._prompt_size[0] + self.input_width + self._input_pad * 2 - 2, self.y))

        if self.value == "" and not self.focused:
            rendered_text = self.font.render(self.default_text, 1, (180, 180, 180))
        else:
            rendered_text = self.font.render(self.value, 1, self.text_color)

        surface.blit(rendered_text, (self.x + self._prompt_size[0] + self._input_pad, self.y))

    def update(self, events):
        """ update the state of the box with the given events """

        if self.locked:
            return

        for event in events:
            if event.type == MOUSEBUTTONDOWN:
                self.focused = self._focus_area.collidepoint(event.pos)
            elif event.type == KEYUP:
                self._update_modifier_level(event, -1)
            elif event.type == KEYDOWN:
                self._update_modifier_level(event, 1)

                if not self.focused:
                    continue

                self._handle_backspace(event)
                self._add_key(event)

    def _update_modifier_level(self, event, delta):
        """ updates the modifier level is meta keys are pressed """

        if event.key == K_LSHIFT or event.key == K_RSHIFT:
            self.shifted += delta
            self.shifted = max(self.shifted, 0)
        elif event.key == K_LALT or event.key == K_RALT:
            self.alt += delta
            self.alt = max(self.alt, 0)
        elif event.key in {K_LMETA, K_RMETA, K_LCTRL, K_RCTRL}:
            self.meta += delta
            self.meta = max(self.meta, 0)

    def _handle_backspace(self, event):
        """ handles the backspace key depending on which modifier keys are pressed """

        if not event.key == K_BACKSPACE:
            return

        if self.meta > 0:
            self.value = ""
        elif self.alt > 0:
            self.value = self.value.rstrip()
            self.value = self.value[:self.value.rfind(' ') + 1]
        elif self.meta == 0:
            self.value = self.value[:-1]

    def _add_key(self, event):
        """ adds the given key to the user text """

        if len(self.value) == self.max_length >= 0:
            return

        if self.meta > 0:
            if event.key == K_x:
                pyperclip.copy(self.value)
                self.value = ''
                return
            elif event.key == K_c:
                pyperclip.copy(self.value)
                return
            elif event.key == K_v:
                self.value += pyperclip.paste()
                return

        if self.shifted:
            key = self.shifted_keys.get(event.key, '')
        else:
            key = self.unshifted_keys.get(event.key, '')

        if key in self.allowed_chars:
            self.value += key


class RadioButton(InputObject):
    BUTTON_RADIUS = 8

    def __init__(self, name, label, pos=(0, 0), text_color=(0, 0, 0), on_change=None, font=None):

        pygame.init()

        self.name = name
        self.label = ' ' + label

        self._pos = pos
        self.text_color = text_color
        self.on_change = on_change
        if font is None:
            self.font = pygame.font.SysFont(get_default_font(), 24)
        else:
            self.font = font

        self._rendered_label = self.font.render(self.label, 1, self.text_color)
        self._label_size = self._rendered_label.get_size()
        self._radio_button_pos = None
        self._label_focus_area = None
        self._recalculate_boxes()

        self._selected = False
        self.focused = False
        self._locked = False

    # getters and setters for position

    @property
    def x(self):
        return self._pos[0]

    @property
    def y(self):
        return self._pos[1]

    @property
    def pos(self):
        return self._pos

    @pos.setter
    def pos(self, value):
        self._pos = value
        self._recalculate_boxes()

    def _recalculate_boxes(self):
        """ recalculate the bounding boxes once the position is changed """

        self._radio_button_pos = (self.x + self.BUTTON_RADIUS, self.y + self._label_size[1] // 2)
        self._label_focus_area = pygame.Rect((self.x + self.BUTTON_RADIUS * 2, self.y), self._label_size)

    # getter and setter for locked property

    @property
    def locked(self):
        return self._locked

    @locked.setter
    def locked(self, value):
        self._locked = value
        if self._locked:
            self.focused = False

    def toggle_lock(self):
        """ convenience method for switching the lock state """

        self.locked = not self.locked

    # getter and setter for value property

    @property
    def value(self):
        return self._selected

    @value.setter
    def value(self, value):
        if self._selected == value:
            return

        if type(value) is not bool:
            return

        self._selected = value

        try:
            self.on_change()
        except TypeError:
            pass

    def draw(self, surface):
        """ draw the radio button on the given surface """

        surface.blit(self._rendered_label, (self.x + self.BUTTON_RADIUS * 2, self.y))

        if self.value:
            pygame.draw.circle(surface, (43, 128, 255), self._radio_button_pos, self.BUTTON_RADIUS)
            pygame.draw.circle(surface, (255, 255, 255), self._radio_button_pos, self.BUTTON_RADIUS // 4)
        else:
            pygame.draw.circle(surface, (150, 150, 150), self._radio_button_pos, self.BUTTON_RADIUS, 1)

    def update(self, events):
        """ update the state of the box with the given events """

        if self.locked:
            return

        for event in events:
            if event.type == MOUSEBUTTONDOWN:
                self.focused = bool(self._label_focus_area.collidepoint(event.pos)) or \
                               ((event.pos[0] - self._radio_button_pos[0]) ** 2 +
                                (event.pos[1] - self._radio_button_pos[1]) ** 2 < self.BUTTON_RADIUS ** 2)
                self.value = self.value or self.focused


class RadioGroup(InputObject):
    def __init__(self, name, selected=-1, on_change=None):
        self.name = name
        self.on_change = on_change

        self.radio_buttons = []
        self.id = 0

        self._selected = selected

    # getter and setter for value property

    @property
    def value(self):
        return self.radio_buttons[self._selected].name

    @value.setter
    def value(self, value):
        if self._selected == value:
            return

        if type(value) is not int:
            return

        self._selected = value

        for i in range(len(self.radio_buttons)):
            if i != value:
                self.radio_buttons[i].value = False

        self.radio_buttons[value].value = True

        try:
            self.on_change()
        except TypeError:
            pass

    def __len__(self):
        return len(self.radio_buttons)

    def _on_change_function(self, change_id):
        def ret():
            self._update_function(change_id)

        return ret

    def _update_function(self, change_id):
        if not self.radio_buttons[change_id].value:
            return

        for i in range(len(self.radio_buttons)):
            if i != change_id:
                self.radio_buttons[i].value = False

        self.value = change_id

    def add_button(self, radio_button):
        """ add a radio button to track """

        if type(radio_button) is not RadioButton:
            return

        if self.id == self._selected:
            radio_button._selected = True
        radio_button.on_change = self._on_change_function(self.id)
        self.radio_buttons.append(radio_button)
        self.id += 1

    def remove_button(self, radio_button):
        """" remove a radio button from tracking """

        radio_button.on_change = None
        self.radio_buttons.remove(radio_button)

    def draw(self, screen):
        """ draw all the radio buttons on the given surface """

        for r in self.radio_buttons:
            r.draw(screen)

    def update(self, events):
        """ update all radio buttons with the given events """

        for r in self.radio_buttons:
            r.update(events)


class CheckBox(InputObject):
    BOX_SIDE_LENGTH = 16

    def __init__(self, name, label, pos=(0, 0), text_color=(0, 0, 0), on_change=None, font=None):

        pygame.init()

        self.name = name
        self.label = ' ' + label

        self._pos = pos
        self.text_color = text_color
        self.on_change = on_change
        if font is None:
            self.font = pygame.font.SysFont(get_default_font(), 24)
        else:
            self.font = font

        self._rendered_label = self.font.render(self.label, 1, self.text_color)
        self._label_size = self._rendered_label.get_size()
        self._checkbox_rect = None
        self._label_focus_area = None
        self._recalculate_boxes()

        self._selected = False
        self.focused = False
        self._locked = False

    # getters and setters for position

    @property
    def x(self):
        return self._pos[0]

    @property
    def y(self):
        return self._pos[1]

    @property
    def pos(self):
        return self._pos

    @pos.setter
    def pos(self, value):
        self._pos = value
        self._recalculate_boxes()

    def _recalculate_boxes(self):
        """ recalculate the bounding boxes once the position is changed """

        self._checkbox_rect = pygame.Rect(self.x, self.y + self._label_size[1] // 2 - self.BOX_SIDE_LENGTH // 2,
                                          self.BOX_SIDE_LENGTH, self.BOX_SIDE_LENGTH)
        self._label_focus_area = pygame.Rect((self.x + self.BOX_SIDE_LENGTH, self.y), self._label_size)

    # getter and setter for locked property

    @property
    def locked(self):
        return self._locked

    @locked.setter
    def locked(self, value):
        self._locked = value
        if self._locked:
            self.focused = False

    def toggle_lock(self):
        """ convenience method for switching the lock state """

        self.locked = not self.locked

    # getter and setter for value property

    @property
    def value(self):
        return self._selected

    @value.setter
    def value(self, value):
        if self._selected == value:
            return

        if type(value) is not bool:
            return

        self._selected = value

        try:
            self.on_change()
        except TypeError:
            pass

    def draw(self, surface):
        """ draw the radio button on the given surface """

        surface.blit(self._rendered_label, (self.x + self.BOX_SIDE_LENGTH, self.y))

        p1 = list(self._checkbox_rect.center)
        p1[0] -= self.BOX_SIDE_LENGTH // 3

        p2 = list(self._checkbox_rect.center)
        p2[0] -= self.BOX_SIDE_LENGTH // 8
        p2[1] += self.BOX_SIDE_LENGTH // 4

        p3 = list(self._checkbox_rect.center)
        p3[0] += self.BOX_SIDE_LENGTH // 4
        p3[1] -= self.BOX_SIDE_LENGTH // 3

        if self.value:
            pygame.draw.rect(surface, (43, 128, 255), self._checkbox_rect, 0)
            pygame.draw.lines(surface, (255, 255, 255), False, (p1, p2, p3), 2)
        else:
            pygame.draw.rect(surface, (150, 150, 150), self._checkbox_rect, 1)

    def update(self, events):
        """ update the state of the box with the given events """

        if self.locked:
            return

        for event in events:
            if event.type == MOUSEBUTTONDOWN:
                self.focused = bool(self._label_focus_area.collidepoint(event.pos)) or \
                               bool(self._checkbox_rect.collidepoint(event.pos))
                self.value = self.focused ^ self.value


class CheckBoxGroup(InputObject):
    def __init__(self, name, on_change=None):
        self.name = name
        self.on_change = on_change

        self.checkboxes = []
        self.id = 0

        self._selected = []

    # getter and setter for value property

    @property
    def value(self):
        return self._selected

    def set_value(self, iden, value):
        if (iden in self._selected) == value:
            return

        if type(iden) is not int or type(value) is not bool:
            return

        if value:
            self._selected.append(iden)
        else:
            self._selected.remove(iden)

        try:
            self.on_change()
        except TypeError:
            pass

    def __len__(self):
        return len(self.checkboxes)

    def _on_change_function(self, change_id):
        def ret():
            self._update_function(change_id)

        return ret

    def _update_function(self, change_id):
        self.set_value(change_id, self.checkboxes[change_id].value)

    def add_checkbox(self, checkbox):
        """ add a checkbox to track """

        if type(checkbox) is not CheckBox:
            return

        checkbox.on_change = self._on_change_function(self.id)
        self.checkboxes.append(checkbox)
        self.id += 1

    def remove_button(self, radio_button):
        """" remove a checkbox from tracking """

        radio_button.on_change = None
        self.checkboxes.remove(radio_button)

    def draw(self, screen):
        """ draw all the checkboxes on the given surface """

        for r in self.checkboxes:
            r.draw(screen)

    def update(self, events):
        """ update all checkboxes with the given events """

        for r in self.checkboxes:
            r.update(events)


class Form(InputObject):
    def __init__(self, name, on_change=None):
        self.name = name
        self.on_change = on_change

        self.form_objects = {}

    # getter and setter for value property

    @property
    def value(self):
        ret = {}
        for e in self.form_objects:
            if not isinstance(self.form_objects[e], Label):
                ret[e] = self.form_objects[e].value

        return ret

    def __len__(self):
        return len(self.form_objects)

    def set_value(self, name, value):
        if name not in self.form_objects:
            return

        if name in self.form_objects and self.form_objects[name] == value:
            return

        if type(name) is not str:
            return

        self.form_objects[name] = value

        try:
            self.on_change()
        except TypeError:
            pass

    def _on_change_function(self):
        try:
            self.on_change()
        except TypeError:
            pass

    def add_form_object(self, form_object):
        """ add a checkbox to track """

        form_object.on_change = self._on_change_function
        self.form_objects[form_object.name] = form_object

    def remove_form_object(self, form_object):
        """" remove a checkbox from tracking """

        form_object.on_change = None
        self.form_objects.pop(form_object)

    def draw(self, screen):
        """ draw all the checkboxes on the given surface """

        for r in self.form_objects:
            self.form_objects[r].draw(screen)

    def update(self, events):
        """ update all checkboxes with the given events """

        for r in self.form_objects:
            self.form_objects[r].update(events)
