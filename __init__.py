'''
Bezier AnimLabel
==============

Use AnimLabel to make letters of a Label follow an user-defined Bezier
curve during an animation.

The example allows to draw a bezier curve, define animation parameters,
and export the points to csv for integration into programs.
'''
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.lang import Builder
from kivy.properties import ListProperty, BooleanProperty, \
    AliasProperty
from kivy.garden.animlabel import AnimLabel
from math import cos, sin, pi, radians
from kivy.vector import Vector

KV = '''
#:import chain itertools.chain
#:import dp kivy.metrics.dp

<BezierTest>:
    canvas:
        Line:
            bezier: self.points
            close: self.loop

        Point:
            points: self.points
            pointsize: 5

        Line:
            points: self.points

    BezierLabel:
        id: label
        points: root.points
        letter_duration: duration_slider.value
        letter_offset: offset_slider.value
        transform: self.bezier
        target_text: ti.text
        font_size: dp(font_size_slider.value)
        transition_function: 'out_elastic'

    Label:
        text: str(label.bezier_length)
        size_hint: None, None
        size: self.texture_size

    BoxLayout:
        size_hint_x: None
        width: '250dp'
        pos_hint: {'right': 1}
        orientation: 'vertical'
        ValueSlider:
            id: duration_slider
            value: 5
            min: 0.01
            max: 10

        ValueSlider:
            id: offset_slider
            value: .1
            min: 0.01
            max: 10

        ValueSlider:
            id: font_size_slider
            value: 50
            min: 10
            max: 100

        TextInput:
            id: ti
            multiline: False
            size_hint_x: None
            width: 250

        ValueSlider:
            id: progress
            value: label._time
            on_value: label._time = self.value
            min: 0
            max: label.letter_duration + label.letter_offset + len(label.target_text)

        Button:
            text: 'play!'
            on_press: label.animate()
            size_hint_x: None
            width: '50dp'


<ValueSlider@BoxLayout>:
    value: slider.value
    on_value: slider.value = self.value
    min: slider.min
    on_min: slider.min = self.min
    max: slider.max
    on_max: slider.max = self.max

    Label:
        text: str(root.value)
    Slider:
        id: slider
'''


def compute_bezier(points, n):
    '''compute nth segment point among segments of the bezier line
    defined by points

    Beware, complexity is quadratic to the number of points
    '''
    # http://en.wikipedia.org/wiki/De_Casteljau%27s_algorithm
    # as the list is in the form of (x1, y1, x2, y2...) iteration is
    # done on each item and the current item (xn or yn) in the list is
    # replaced with a calculation of "xn + x(n+1) - xn" x(n+1) is
    # placed at n+2. each iteration makes the list one item shorter
    P = points[:]

    for i in range(1, len(P)):
        for j in range(len(P) - 2 * i):
            P[j] = P[j] + (P[j + 2] - P[j]) * n

    # we got the coordinates of the point in T[0] and T[1]
    return P[0], P[1]


class BezierLabel(AnimLabel):
    points = ListProperty()

    def compute_bezier_length(self, *args):
        if not self.points:
            return 0

        a = 0
        l = 0
        v = Vector(compute_bezier(self.points, 0))

        while a < 1:
            a += 0.01
            p = compute_bezier(self.points, a)
            l += v.distance(p)
            v = Vector(p)
        return l

    bezier_length = AliasProperty(
        compute_bezier_length, cache=True, bind=['points', ])

    def bezier(self, points, progress):
        # XXX for now we don't care about the original position, so
        # kerning is out, along any sane spacing, this is an experiment
        if not self.points:
            return (0, 0, 0, 0, 0, 0, 0, 0)

        d_ratio = 1 / (self.bezier_length or 1)

        x0, y0, x1, y1 = points

        # initial letter offset of the letter
        dx = (x1 + x0) / 2 - (self.center_x - self.texture_size[0] / 2)
        # convert it to a progress offset on the bezier curve
        da = dx * d_ratio

        progress = progress - da

        w = x1 - x0
        h = y1 - y0
        e = 0.01
        b1 = compute_bezier(
            self.points,
            max(0, progress - e))
        b2 = compute_bezier(
            self.points,
            min(progress + e, 1))

        cx = (b2[0] + b1[0]) / 2
        cy = (b2[1] + b1[1]) / 2
        a = - pi / 2 + radians((Vector(b2) - Vector(b1)).angle((0, 1)))

        print(progress, a)
        if not 0 <= progress < 1 + e:
            a += pi

        return (
            cx + cos(a - 3 * pi / 4) * w / 2, cy + sin(a - 3 * pi / 4) * h / 2,
            cx + cos(a - 1 * pi / 4) * w / 2, cy + sin(a - 1 * pi / 4) * h / 2,
            cx + cos(a + 1 * pi / 4) * w / 2, cy + sin(a + 1 * pi / 4) * h / 2,
            cx + cos(a + 3 * pi / 4) * w / 2, cy + sin(a + 3 * pi / 4) * h / 2,
        )


class BezierTest(FloatLayout):
    points = ListProperty()
    loop = BooleanProperty()

    def __init__(self, points=[], loop=False, *args, **kwargs):
        super(BezierTest, self).__init__(*args, **kwargs)
        self.d = 10  # pixel tolerance when clicking on a point
        self.points = points
        self.loop = loop

    def on_touch_down(self, touch):
        if self.collide_point(touch.pos[0], touch.pos[1]):
            points = list(zip(self.points[::2], self.points[1::2]))
            for i, p in enumerate(points):
                if (
                    abs(touch.pos[0] - self.pos[0] - p[0]) < self.d and
                    abs(touch.pos[1] - self.pos[1] - p[1]) < self.d
                ):
                    if touch.is_double_tap:
                        self.points.pop(i * 2)
                        self.points.pop(i * 2)
                        return True
                    touch.ud['current_point'] = i + 1
                    touch.grab(self)
                    return True

            if touch.is_double_tap:
                # find the nearest point
                if not points:
                    self.add_point(0, touch)
                    return

                v = Vector(touch.pos)
                pts = sorted(enumerate(points), key=lambda x: v.distance(x[1]))
                ids = [x[0] for x in pts]
                if ids[0] == 0:
                    # insert before 1st
                    idx = 0
                elif ids[0] == len(ids) - 1:
                    # insert after last
                    idx = len(ids)
                elif ids.index(ids[0] - 1) < ids.index(ids[0] + 1):
                    idx = ids[0]
                else:
                    idx = ids[0] + 1

                self.add_point(idx, touch)
            # insert a point between them, at position of the touch
        return super(BezierTest, self).on_touch_down(touch)

    def add_point(self, idx, touch):
        self.points.insert(idx * 2, touch.x)
        self.points.insert(idx * 2 + 1, touch.y)
        touch.grab(self)
        touch.ud['current_point'] = idx + 1

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
        else:
            return super(BezierTest, self).on_touch_up(touch)

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            c = touch.ud['current_point']
            self.points[(c - 1) * 2] = touch.pos[0] - self.pos[0]
            self.points[(c - 1) * 2 + 1] = touch.pos[1] - self.pos[1]
            return True
        return super(BezierTest, self).on_touch_move(touch)


class Main(App):

    def build(self):
        Builder.load_string(KV)
        from math import cos, sin, radians
        x = y = 150
        l = 100
        # Pacman !
        points = [x, y]
        for i in range(45, 360, 45):
            i = radians(i)
            points.extend([x + cos(i) * l, y + sin(i) * l])
        return BezierTest(points=points)

if __name__ == '__main__':
    Main().run()
