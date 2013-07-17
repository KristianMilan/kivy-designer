from kivy.uix.scatter import ScatterPlane
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.layout import Layout
from kivy.properties import ObjectProperty, BooleanProperty
from kivy.app import App
from kivy.uix.filechooser import FileChooserListView, FileChooserIconView
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.sandbox import Sandbox
from kivy.factory import Factory
from kivy.base import EventLoop

from designer.common import widgets
from designer.tree import Tree
from designer.undo_manager import WidgetOperation

class PlaygroundDragElement(BoxLayout):
    '''An instance of this class is the drag element shown when user tries to
       add a widget to :class:`~designer.playground.Playground` by dragging
       from :class:`~designer.toolbox.Toolbox` to 
       :class:`~designer.playground.Playground`.
    '''

    playground = ObjectProperty()
    '''Reference to the :class:`~designer.playground.Playground`
       :data:`playground` is a :class:`~kivy.properties.ObjectProperty`
    '''

    target = ObjectProperty(allownone=True)
    '''Widget where widget is to be added.
       :data:`target` a :class:`~kivy.properties.ObjectProperty`
    '''
    can_place = BooleanProperty(False)
    '''Whether widget can be added or not.
       :data:`can_place` is a :class:`~kivy.properties.BooleanProperty`
    '''

    def on_touch_move(self, touch):
        '''This is responsible for moving the drag element and showing where
           the widget it contains will be added.
        '''

        if touch.grab_current is self:
            self.center_x = touch.x
            self.y = touch.y + 20
            self.target = self.playground.try_place_widget(
                    self.children[0], self.center_x, self.y - 20)
            self.can_place = self.target is not None
            return True

    def on_touch_up(self, touch):
        '''This is responsible for adding the widget to the parent
        '''
        if touch.grab_current is self:
            touch.ungrab(self)
            self.target = self.playground.try_place_widget(
                    self.children[0], self.center_x, self.y - 20)
            self.can_place = self.target is not None
            if self.can_place or self.playground.root is None:
                child = self.children[0]
                child.parent.remove_widget(child)
                self.playground.place_widget(
                        child, self.center_x, self.y - 20)
            self.parent.remove_widget(self)
            return True


class Playground(ScatterPlane):
    '''Playground represents the actual area where user will add and delete
       the widgets. It has event on_show_edit, which is emitted whenever 
       Playground is clicked.
    '''

    root = ObjectProperty(allownone=True)
    '''This property represents the root widget.
       :data:`root` is a :class:`~kivy.properties.ObjectProperty`
    '''

    selection_mode = BooleanProperty(True)
    '''
       :data:`can_place` is a :class:`~kivy.properties.BooleanProperty`
    '''

    tree = ObjectProperty()

    clicked = BooleanProperty(False)
    '''This property represents whether 
       :class:`~designer.playground.Playground` has been clicked or not
       :data:`clicked` is a :class:`~kivy.properties.BooleanProperty`
    '''

    sandbox = ObjectProperty(None)
    '''This property represents the sandbox widget which is added to
       :class:`~designer.playground.Playground`.
       :data:`sandbox` is a :class:`~kivy.properties.ObjectProperty`
    '''

    kv_code_input = ObjectProperty()
    '''This property refers to the 
       :class:`~designer.ui_creator.UICreator`'s KVLangArea.
       :data:`kv_code_input` is a :class:`~kivy.properties.ObjectProperty`
    '''

    widgettree = ObjectProperty()
    '''This property refers to the
       :class:`~designer.ui_creator.UICreator`'s WidgetTree.
       :data:`widgettree` is a :class:`~kivy.properties.ObjectProperty`
    '''

    __events__ = ('on_show_edit',)

    def __init__(self, **kwargs):
        super(Playground, self).__init__(**kwargs)
        self.tree = Tree()
        self.keyboard = None
        self.selected_widget = None
        self.undo_manager = None

    def on_show_edit(self, *args):
        pass

    def try_place_widget(self, widget, x, y):
        '''This function is used to determine where to add the widget
        '''

        x, y = self.to_local(x, y)
        return self.find_target(x, y, self.root, widget)

    def on_root(self, instance, value):
        pass #self.tree.insert(value, None)

    def place_widget(self, widget, x, y):
        '''This function is used to first determine the target where to add 
           the widget. Then it add that widget.
        '''

        x, y = self.to_local(x, y)
        target = self.find_target(x, y, self.root, widget)
        #wx, wy = target.to_widget(x, y)
        #widget.pos = wx, wy
        widget.pos = 0, 0
        self.add_widget_to_parent(widget, target)

    def add_widget_to_parent(self, widget, target, from_undo=False, from_kv=False, kv_str=''):
        '''This function is used to add the widget to the target.
        '''

        added = False
        if target is None:
            with self.sandbox:
                self.root = widget
                self.sandbox.add_widget(widget)
                widget.size = self.sandbox.size
                added = True

        else:
            with self.sandbox:
                target.add_widget(widget)
                added = True
                #Added just for testing, clicking on the 
                #playground will lead an error, but inside sandbox
                #widget.bind(on_touch_down=widget)

        #self.tree.insert(widget, target)
        if not added:
            return False
        
        self.widgettree.refresh()

        if not from_kv:
            self.kv_code_input.add_widget_to_parent(widget, target,
                                                    kv_str=kv_str)

        if not from_undo:
            root = App.get_running_app().root
            root.undo_manager.push_operation(WidgetOperation('add', 
                                                             widget, target,
                                                             self, ''))

    def get_widget(self, widgetname, **default_args):
        '''This function is used to get the instance of class of name,
           widgetname.
        '''

        widget = None
        with self.sandbox:
            custom = False
            for _widget in widgets:
                if _widget[0] == widgetname and _widget[1] == 'custom':
                    widget = App.get_running_app().root\
                        .project_loader.get_widget_of_class(widgetname)
                    custom = True
            if not custom:
                try:
                    widget = getattr(Factory, widgetname)(**default_args)
                except:
                    pass

        return widget

    def get_playground_drag_element(self, widgetname, touch, **default_args):
        '''This function will return the desired playground element
           for widgetname.
        '''

        widget = self.get_widget(widgetname, **default_args)
        container = PlaygroundDragElement(playground=self)
        container.add_widget(widget)
        touch.grab(container)
        container.center_x = touch.x
        container.y = touch.y + 20
        return container
    
    def cleanup(self):
        '''This function is used to clean the state of Playground, cleaning
           the changes done by currently opened project.
        '''

        #Cleanup is called when project is created or loaded
        #so this operation shouldn't be recorded in Undo
        if self.root:
            self.remove_widget_from_parent(self.root, True)

        self.tree = Tree()

    def remove_widget_from_parent(self, widget, from_undo=False, from_kv=False):
        '''This function is used to remove widget its parent.
        '''

        parent = None
        root = App.get_running_app().root
        if not widget:
            return

        removed_str = ''
        if not from_kv:
            removed_str = self.kv_code_input.remove_widget_from_parent(widget,
                                                                       parent)
        if widget != self.root:
            parent = widget.parent
            parent.remove_widget(widget)
        else:
            print 'parent removed'
            self.root.parent.remove_widget(self.root)
            self.root = None

        #self.tree.delete(widget)
        root.ui_creator.widgettree.refresh()
        if not from_undo:
            root.undo_manager.push_operation(
                WidgetOperation('remove', widget, parent, self, removed_str))

    def find_target(self, x, y, target, widget=None):
        '''This widget is used to find the widget which collides with x,y
        '''
        if target is None or not target.collide_point(x, y):
            return None

        x, y = target.to_local(x, y)
        class_rules = App.get_running_app().root.project_loader.class_rules

        for child in target.children:
            is_child_custom = False
            for rule in class_rules:
                if rule.name == type(child).__name__:
                    is_child_custom = True
                    break
            
            #if point lies in custom wigdet's child then return custom widget
            if is_child_custom:
                if not widget and self._custom_widget_collides(child, x, y):
                    return child
                elif widget:
                    return target
            else:
                if not child.collide_point(x, y):
                    continue
    
                if not self.allowed_target_for(child, widget):
                    continue

                return self.find_target(x, y, child, widget)
        return target
    
    def _custom_widget_collides(self, widget, x, y):
        '''This widget is used to find which custom widget collides with x,y
        '''
        if not widget:
            return False

        if widget.collide_point(x, y):
            return True
        
        x, y = widget.to_local(x, y)

        for child in widget.children:
            if self._custom_widget_collides(child, x, y):
                return True
        
        return False
    
    def allowed_target_for(self, target, widget):
        '''This function is used to determine if widget could be added to 
           target.
        '''
        # stop on complex widget
        t = target if widget else target.parent
        if isinstance(t, FileChooserListView):
            return False
        if isinstance(t, FileChooserIconView):
            return False
        
        # stop on custom widget but not root widget
        class_rules = App.get_running_app().root.project_loader.class_rules
        root_widget = App.get_running_app().root.project_loader.root_rule.widget

        # if we don't have widget, always return true
        if widget is None:
            return True

        is_widget_layout = isinstance(widget, Layout)
        is_target_layout = isinstance(target, Layout)
        if is_widget_layout and is_target_layout:
            return True
        if is_target_layout:
            return True
        return False
    
    def _keyboard_released(self, *args):
        '''Called when self.keyboard is released
        '''
        self.keyboard.unbind(on_key_down=self._on_keyboard_down)
        self.keyboard = None
    
    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
        '''Called when a key on keyboard is pressed
        '''
        if modifiers != [] and modifiers[-1] == 'ctrl':
            if keycode[1] == 'c':
                self.do_copy()

            elif keycode[1] == 'v':
                self.do_paste()

            elif keycode[1] == 'x':
                self.do_cut()
            
            elif keycode[1] == 'a':
                self.do_select_all()

            elif keycode[1] == 'z':
                self.do_undo()
            
            elif modifiers [0] == 'shift' and keycode[1] == 'z':
                self.do_redo()
            
        elif keycode[1] == 'delete':
            self.do_delete()
    
    def do_undo(self):
        '''Undoes the last operation
        '''
        self.undo_manager.do_undo()
    
    def do_redo(self):
        '''Undoes the last operation
        '''
        self.undo_manager.do_redo()

    def do_copy(self):
        '''Copy the selected widget
        '''
        base_widget = self.selected_widget
        if base_widget:
            self.widget_to_paste = type(base_widget)()
            props = base_widget.properties()
            for prop in props:
                setattr(self.widget_to_paste, prop,
                        getattr(base_widget, prop))

            self.widget_to_paste.parent = None
            self._widget_str_to_paste = self.kv_code_input.\
                get_widget_text_from_kv(base_widget, None)
    
    def do_paste(self):
        '''Paste the selected widget to the current widget
        '''
        parent = self.selected_widget
        if parent and self.widget_to_paste:

            #find appropriate parent to add widget_to_paste
            while parent and not isinstance(parent, Layout):
                parent = parent.parent

            if parent is not None:
                self.add_widget_to_parent(self.widget_to_paste,
                                          parent,
                                          kv_str=self._widget_str_to_paste)
                self.widget_to_paste = None
    
    def do_cut(self):
        '''Cuts the selected widget
        '''
        base_widget = self.selected_widget

        if base_widget:
            self.widget_to_paste = base_widget
            self._widget_str_to_paste = self.kv_code_input.\
                get_widget_text_from_kv(base_widget, None)

            self.remove_widget_from_parent(base_widget)
    
    def do_select_all(self):
        '''Select All widgets which basically means selecting root widget
        '''
        self.selected_widget = self.root
        App.get_running_app().focus_widget(self.root)
    
    def do_delete(self):
        '''Delete the selected widget
        '''
        if self.selected_widget:
            self.remove_widget_from_parent(self.selected_widget)

    def on_touch_down(self, touch):
        '''An override of ScatterPlane's on_touch_down.
           Used to determine the current selected widget and also emits,
           on_show_edit event.
        '''

        if super(ScatterPlane, self).collide_point(*touch.pos) and \
            not self.keyboard:
            win = EventLoop.window
            self.keyboard = win.request_keyboard(self._keyboard_released, self)
            self.keyboard.bind(on_key_down=self._on_keyboard_down)
            
        if self.selection_mode:
            if super(ScatterPlane, self).collide_point(*touch.pos):
                x, y = self.to_local(*touch.pos)
                target = self.find_target(x, y, self.root)
                self.selected_widget = target
                App.get_running_app().focus_widget(target)
                self.clicked = True
                self.dispatch('on_show_edit', Playground)
                return True

        if self.parent.collide_point(*touch.pos):
            super(Playground, self).on_touch_down(touch)

        return False
