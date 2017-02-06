# coding: utf-8
"""
:created: 23.07.12

:author: pirogov
"""
import inspect

from django.db import models as django_models

from m3_ext.ui import all_components as ext
from m3_ext.ui import windows as ext_windows
from m3_ext.ui.misc import store as ext_store

import tools


# =============================================================================
# BaseWindow
# =============================================================================
class BaseWindow(ext_windows.ExtWindow):
    """
    Базовое окно
    """
    def __init__(self):
        super(BaseWindow, self).__init__()
        self._mro_exclude_list = []  # список исключений для make_read_only
        self._init_components()
        self._do_layout()

    def _init_components(self):
        """
        Метод создаёт визуальные компоненты,
        отражающие ПОЛЯ модели, но НЕ ОПРЕДЕЛЯЕТ РАСПОЛОЖЕНИЕ
        компонентов в окне

        Пример::

            self.grid = ext.ExtObjectGrid()

        """
        pass

    def _do_layout(self):
        """
        Метод располагает УЖЕ СОЗДАННЫЕ визуальные компоненты
        на окне, создавая по необходимости контейнеры (ТОЛЬКО контейнеры)

        Пример::

            self.layout = 'fit'
            self.items.append(self.grid)

        """
        pass

    def set_params(self, params):
        """
        Метод принимает словарь, содержащий параметры окна,
        передаваемые в окно слоем экшнов

        .. note::

            Параметры могут содержать общие настройки окна (title, width,
            height, maximized...) и флаг режима для чтения (read_only)

        :param params: Словарь с параметрами
        :type params: dict
        """

        def apply(attr):
            if attr in params:
                setattr(self, attr, params[attr])

        apply('width')
        apply('height')
        apply('maximized')
        apply('maximizable')
        apply('minimizable')
        apply('title')
        self.title = self.title or u''

        if params.get('read_only'):
            self.make_read_only()

    def _make_read_only(self, access_off=True, exclude_list=None):
        """
        Метод управляет режимом "только для чтения" окна

        .. note::

            Потомки могут дополнять список self._mro_exclude_list -
            список визуальных компонентов, которые не будут
            блокироваться в режиме "только для чтения".
            Т.о. метод обычно не требует перекрытья -
            достаточно списка исключений

        :param access_off: True/False - включение/выключение режима
        :type access_off: bool
        :param exclude_list: список компонентов, которые не будут блокироваться
        :type exclude_list: list
        """

        super(BaseWindow, self)._make_read_only(
            access_off, self._mro_exclude_list + (exclude_list or []))


# =============================================================================
# BaseEditWindow
# =============================================================================
class BaseEditWindow(ext_windows.ExtEditWindow, BaseWindow):
    """
    Базовое окно редактирования (с формой и кнопкой сабмита)
    """

    def _init_components(self):
        """
        .. seealso::
            :func:`objectpack.ui.BaseWindow._init_components`
        """
        super(BaseEditWindow, self)._init_components()

        self.form = ext.ExtForm()

        self.save_btn = ext.ExtButton(
            text=u'Сохранить', handler="submitForm")
        self.cancel_btn = ext.ExtButton(
            text=u'Отмена', handler="close")

        # Кнопка "Отмена" не блокируется в режиме "только для чтения"
        self._mro_exclude_list.append(self.cancel_btn)

    def _do_layout(self):
        """
        .. seealso::
            :func:`objectpack.ui.BaseWindow._do_layout`
        """
        super(BaseEditWindow, self)._do_layout()
        # self.modal = True

        self.buttons.extend([
            self.save_btn,
            self.cancel_btn,
        ])

        # Горячая клавиша F2 эквивалентна ОК:
        f2key = {'key': 113, 'fn': self.save_btn.handler}
        self.keys.append(f2key)

    def set_params(self, params):
        """
        .. seealso::
            :func:`objectpack.ui.BaseWindow.set_params`
        """
        # url, по которому находится action/view сохранения
        self.form.url = params['form_url']
        obj = params.get('object', None)
        if obj:
            self.form.from_object(obj)
        super(BaseEditWindow, self).set_params(params)


# =============================================================================
# BaseListWindow
# =============================================================================
class BaseListWindow(BaseWindow):
    """
    Базовое окно списка объектов
    """
    def __init__(self, *args, **kwargs):
        super(BaseListWindow, self).__init__(*args, **kwargs)
        self.grid_filters = {}

    def _init_components(self):
        """
        .. seealso::
            :func:`objectpack.ui.BaseWindow._init_components`
        """
        self.grid = ext.ExtObjectGrid(item_id='grid')
        self.close_btn = self.btn_close = ext.ExtButton(
            name='close_btn',
            text=u'Закрыть',
            handler='close'
        )
        self._mro_exclude_list.extend([
            self.close_btn,
            self.grid.top_bar.button_refresh
        ])

    def _do_layout(self):
        """
        .. seealso::
            :func:`objectpack.ui.BaseWindow._do_layout`
        """
        self.layout = self.FIT
        self.items.append(self.grid)
        self.buttons.append(self.btn_close)

    def set_params(self, params, *args, **kwargs):
        """
        Принимает в параметрах пак и делегирует ему конфигурирование грида

        .. seealso::
            :func:`objectpack.ui.BaseWindow.set_params`
        """
        super(BaseListWindow, self).set_params(params)
        self.maximizable = self.minimizable = True

        assert 'pack' in params, (
            u'Параметры окна должны содержать экземпляр ActionPack'
            u' настраивающего grid!'
        )
        params['pack'].configure_grid(self.grid, *args, **kwargs)

    def add_grid_column_filter(
            self, column_name,
            filter_control=None, filter_name=None, tooltip=None):
        """
        Метод добавляет колоночный фильтр в грид

        :param column_name: Имя колонки
        :type column_name: str
        :param filter_control: Ext-компонент фильтра
        :type filter_control:
        :param filter_name: Имя фильтра
        :type filter_name: str
        :param tooltip: Всплывающая подсказка
        :type tooltip: unicode
        """
        if not filter_name:
            filter_name = column_name
        if column_name in self.grid_filters:
            fltr = self.grid_filters[column_name]
        else:
            fltr = {}

        fltr[filter_name] = {
            'column_name': column_name,
            'filter_control': filter_control,
            'filter_name': filter_name,
            'tooltip': tooltip
        }
        self.grid_filters[column_name] = fltr

    def del_grid_column_filter(self, column_name, filter_name=None):
        """
        Метод удаляет колоночный фильтр

        :param column_name: Имя колонки
        :type column_name: str
        :param filter_name: Имя фильтра
        :type filter_name: str
        """
        if not filter_name:
            filter_name = column_name
        if column_name in self.grid_filters:
            if filter_name in self.grid_filters[column_name]:
                del self.grid_filters[column_name][filter_name]
            if len(self.grid_filters[column_name]) == 0:
                del self.grid_filters[column_name]

    def _render_filter(self, filter_):
        """
        :param filter_: Колоночный фильтр
        :type filter_: dict
        :return: ExtJs-представление фильтра
        :rtype: unicode
        """
        lst = []
        if filter_['filter_control']:
            return filter_['filter_control']
        else:
            lst.append(u'xtype: "textfield"')
        if filter_['tooltip']:
            lst.append(u'tooltip: "%s"' % filter_['tooltip'])
        lst.append(u'filterName: "%s"' % filter_['filter_name'])
        return '{%s}' % ','.join(lst)

    def render(self):
        """
        Рендеринг окна
        """
        if self.grid:
            # добавим характеристики фильтров в колонки и подключим плагин
            if len(self.grid_filters) > 0:
                self.grid.plugins.append('new Ext.ux.grid.GridHeaderFilters()')
            for col in self.grid.columns:
                if col.data_index in self.grid_filters:
                    if len(self.grid_filters[col.data_index]) == 1:
                        filter_str = self._render_filter(
                            self.grid_filters[col.data_index].values()[0])
                    else:
                        filters = []
                        for fltr in self.grid_filters[col.data_index].values():
                            filters.append(self._render_filter(fltr))
                        filter_str = '[%s]' % ','.join(filters)
                    col.extra['filter'] = filter_str
        return super(BaseListWindow, self).render()


# =============================================================================
# BaseSelectWindow
# =============================================================================
class BaseSelectWindow(BaseListWindow):
    """
    Окно выбора из списка объектов
    """

    _xtype = 'objectpack-select-window'

    js_attrs = BaseListWindow.js_attrs.extend(
        grid_item_id='gridItemId',
        column_name_on_select='columnNameOnSelect',
        multi_select='multiSelect',
    )

    def _init_components(self):
        """
        .. seealso::
            :func:`objectpack.ui.BaseWindow._init_components`
        """
        super(BaseSelectWindow, self)._init_components()
        self.select_btn = ext.ExtButton(
            handler='selectValue',
            text=u'Выбрать')
        self._mro_exclude_list.append(self.select_btn)
        self.grid_item_id = self.grid.item_id

    def _do_layout(self):
        """
        .. seealso::
            :func:`objectpack.ui.BaseWindow._do_layout`
        """
        super(BaseSelectWindow, self)._do_layout()
        self.buttons.insert(0, self.select_btn)

    def _enable_multi_select(self):
        """
        Включает множественный выбор в гриде
        """
        self.multi_select = True
        self.grid.sm = ext.ExtGridCheckBoxSelModel()

    def set_params(self, params, *args, **kwargs):
        """
        .. seealso::
            :func:`objectpack.ui.BaseWindow.set_params`
        """
        super(BaseSelectWindow, self).set_params(params, *args, **kwargs)
        if params.get('multi_select', False):
            self._enable_multi_select()

        self.column_name_on_select = params['column_name_on_select']


class BaseMultiSelectWindow(BaseSelectWindow):
    """
    Окно множественного выбора в ExtMultiSelectWindow
    """
    _xtype = 'objectpack-multi-select-window'

    def set_params(self, params):
        super(BaseMultiSelectWindow, self).set_params(params)
        self._enable_multi_select()


# =============================================================================
# ColumnsConstructor
# =============================================================================
class ColumnsConstructor(object):
    """
    Конструктор колонок для сложных гридов с banded-колонками

    Имеет 2 дочерних класса:
    - Col - простая колонка
    - BandedCol - группирующая колонка.

    Пример использования::

        # создание колонок inline

        cc = ColumnsConstructor()
        cc.add(
            cc.Col(header='1'),

            cc.BandedCol(header='2', items=(
                cc.Col(header='3'),
                cc.Col(header='4'),

                cc.BandedCol(header='5', items=(
                    cc.Col(header='6'),

                    cc.BandedCol(header='7', items=(
                        cc.Col(header='8'),
                        cc.Col(header='9'),
                        cc.BandedCol(),
                    )),

                    cc.Col(header='10')
                ))
            )),
            cc.Col(header='11')
        )

        # динамическое создание колонок
        for grp_idx in 'ABCD':
            grp = cc.BandedCol(header=grp_idx)

            for col_idx in 'ABCD':
                grp.add(
                    cc.Col(header=grp_idx + col_idx)
                )

            cc.add(grp)

        cc.configure_grid(grid)

    """

    class BandedCol(object):
        """
        Группирующая колонка
        """

        def __init__(self, items=None, **kwargs):
            """
            :param items: Подчинённые колонки
            :type items: Iterable
            :param kwargs: Передаются в конструктор ExtGridColumn
            :type kwargs: dict
            """
            params = {'header': ''}
            params.update(kwargs)
            self._column = ext.ExtGridColumn(**params)
            self.items = list(items or [])

        def add(self, *args):
            """
            Добавление колонок

            :param args: Колонки
            :type args: list
            """
            self.items.extend(args)

        def _cleaned(self):
            """
            :return: Элемент очищенный от пустых подэлементов
                     или None, если непустых подэлементов нет
            """
            self.items = filter(None, [i._cleaned() for i in self.items])
            return self if self.items else None

        def _normalized_depth(self):
            """
            Приведение всех подэлементов к одному уровню вложенности

            :return: Возвращается максимальная вложенность
            :rtype: int
            """
            depths = [i._normalized_depth() for i in self.items]
            max_depth = max(depths)

            new_items = []
            for depth, item in zip(depths, self.items):
                while depth < max_depth:
                    item = ColumnsConstructor.BandedCol(items=[item])
                    depth += 1
                new_items.append(item)
            self.items = new_items
            return max_depth + 1

        def _populate(self, grid, level, is_top_level=False):
            """
            Вставка колонок. Возвращается кол-во вставленных колонок
            """
            if is_top_level:
                if not self._cleaned():
                    return 0  # чистка
                self._normalized_depth()  # нормализация уровней
                level = 1
            else:
                grid.add_banded_column(self._column, level, 0)

            if not self.items:
                return 0

            cnt = sum([i._populate(grid, level + 1) for i in self.items])
            self._column.colspan = cnt

            return cnt

    class Col(object):
        """
        Простая колонка
        """
        _ext_classes = {
            None: ext.ExtGridColumn,
            'checkbox': ext.ExtGridCheckColumn,
        }

        def __init__(self, **kwargs):
            params = {'header': 'None'}
            params.update(kwargs)

            ui_clazz = params.pop('type', None)
            if not callable(ui_clazz):
                ui_clazz = self._ext_classes[ui_clazz]

            self._column = ui_clazz(**params)

        def _cleaned(self):
            return self

        def _normalized_depth(self):
            return 1  # подэлементов нет, поэтому всегда вложенность 1

        def _populate(self, grid, level, is_top_level=False):
            grid.columns.append(self._column)
            return 1

    def __init__(self, items=None):
        self.items = list(items or [])

    def add(self, *args):
        """
        Добавление колонок
        """
        self.items.extend(args)

    def configure_grid(self, grid):
        """
        Конфигурирование грида
        """
        # все элементы суются в фейковую группирующую колонку,
        # которая отображаться не будет
        fake_col = self.BandedCol(items=self.items)
        fake_col._populate(grid, level=None, is_top_level=True)

    @classmethod
    def from_config(cls, config, ignore_attrs=None):
        """
        Создание экземпляра на основе конфигурации :attr:`config`

        :param config:
        :type config: dict
        :param ignore_attrs:
        :type ignore_attrs:
        """
        cc = cls()

        def populate(root, cols):
            for c in cols:
                # параметры создаваемой колонки
                params = {}
                params.update(c)
                sub_cols = params.pop('columns', None)

                # удаляются атрибуты, указанные игнорируемыми
                for a in (ignore_attrs or []):
                    params.pop(a, None)

                params['header'] = unicode(params.pop('header', ''))
                if sub_cols is not None:
                    new_root = cc.BandedCol(**params)
                    root.add(new_root)
                    populate(new_root, sub_cols)
                else:
                    root.add(cc.Col(**params))

        populate(cc, config)
        return cc


# =============================================================================
# ModelEditWindow
# =============================================================================
class ModelEditWindow(BaseEditWindow):
    """
    Простое окно редактирования модели
    """

    model = None
    """
    Модель, для которой будет строиться окно
    """

    field_fabric_params = None
    """
    Словарь kwargs для model_fields_to_controls ("field_list", и т.д.)
    """

    def _init_components(self):
        """
        .. seealso::
            :func:`objectpack.ui.BaseWindow._init_components`
        """
        super(ModelEditWindow, self)._init_components()
        self._controls = model_fields_to_controls(
            self.model, self, **(self.field_fabric_params or {}))

    def _do_layout(self):
        """
        .. seealso::
            :func:`objectpack.ui.BaseWindow._do_layout`
        """
        super(ModelEditWindow, self)._do_layout()

        # автоматически вычисляемая высота окна
        # self.height = None
        self.layout = self.FORM
        self.layout_config = {'autoHeight': True}
        self.form.layout_config = {'autoHeight': True}

        # все поля добавляются на форму растянутыми по ширине
        self.form.items.extend(map(anchor100, self._controls))

    def set_params(self, params):
        """
        .. seealso::
            :func:`objectpack.ui.BaseWindow.set_params`
        """
        super(ModelEditWindow, self).set_params(params)
        # если сгенерировано хотя бы одно поле загрузки файлов,
        # окно получает флаг разрешения загрузки файлов
        self.form.file_upload = any(
            isinstance(x, ext.ExtFileUploadField)
            for x in self._controls)

    @classmethod
    def fabricate(cls, model, **kwargs):
        """
        Гененрирует класс-потомок для конкретной модели

        Использование::

            class Pack(...):
                add_window = ModelEditWindow.fabricate(
                    SomeModel,
                    field_list=['code', 'name'],
                    model_register=observer,
                )

        :param model: Модель django
        :type model: django.db.models.Model
        :param kwargs: Параметры для передачи в field_fabric_params
        :type kwargs: dict
        :return: Субкласс objectpack.ui.ModelEditWindow
        """
        return type('%sEditWindow' % model.__name__, (cls,), {
            'model': model, 'field_fabric_params': kwargs})


# =============================================================================
def model_fields_to_controls(
        model, window,
        field_list=None, exclude_list=None,
        model_register=None, **kwargs):
    """
    Добавление на окно элементов формы по полям модели

    .. note::
        :attr:`exclude_list` игнорируется при указанном :attr:`field_list`

    .. note::
        Списки включения/исключения полей могут содержать
        wildcards вида `x*` или `*x`,
        которые трактуются как префиксы и суффиксы

    .. note::
        При создании полей для связанных моделей ActionPack для модели ищется
        в реестре моделей :attr:`model_register` по имени класса модели
        (передачей имени в метод "get" реестра)

    :param model: Модель django
    :type mode: django.db.models.Model
    :param window: Окно
    :type window: m3_ext.ui.windows.window.ExtWindow
    :param field_list: Список полей
    :type field_list: list
    :param exclude_list: Список полей-исключений
    :type exclude_list: list
    :param model_register: Реестр моделей-паков
    :param kwargs: Дополнительные параметры для передачи в
    конструктор элементов
    :type kwargs: dict
    :return: Список контролов для полей модели
    :rtype: list
    """
    def make_checker(patterns):
        matchers = []
        for pattern in patterns:
            if pattern.endswith('*'):
                fn = (lambda p: lambda s: s.startswith(p))(pattern[:-1])
            elif pattern.startswith('*'):
                fn = (lambda p: lambda s: s.endswith(p))(pattern[1:])
            else:
                fn = (lambda p: lambda s: s == p)(pattern)
            matchers.append(fn)
        if matchers:
            return (lambda s: any(fn(s) for fn in matchers))
        else:
            return lambda s: True

    if field_list:
        # генерация функции, разрешающей обработку поля
        is_valid = make_checker(list(field_list or ()))
    else:
        # генерация функции, запрещающей обработку поля
        is_valid = (lambda fn: lambda x: not fn(x))(
            make_checker(list(exclude_list or ()) + [
                'created', '*.created',
                'modified', '*.modified',
                'external_id', '*.external_id',
            ]))

    controls = []
    for f in model._meta.fields:
        if is_valid(f.attname):
            try:
                ctl = _create_control_for_field(f, model_register, **kwargs)
            except GenerationError:
                continue

            setattr(window, 'field__%s' % f.attname.replace('.', '__'), ctl)
            controls.append(ctl)

    return controls


class GenerationError(Exception):
    """
    ошибка возникает при проблемы генерации контрола
    """
    pass


def _create_control_for_field(f, model_register=None, **kwargs):
    """
    создает контрол для поля f = models.Field from model
    """
    name = f.attname

    if f.choices:
        ctl = make_combo_box(data=list(f.choices), **kwargs)

    elif isinstance(f, django_models.BooleanField):
        ctl = ext.ExtCheckBox(**kwargs)

    elif isinstance(f, django_models.CharField):
        ctl = ext.ExtStringField(max_length=f.max_length, **kwargs)

    elif isinstance(f, django_models.TextField):
        ctl = ext.ExtTextArea(**kwargs)

    elif isinstance(f, django_models.IntegerField):
        ctl = ext.ExtNumberField(**kwargs)
        ctl.allow_decimals = False
        if isinstance(f, (django_models.PositiveIntegerField,
                          django_models.PositiveSmallIntegerField)):
            ctl.allow_negative = False

    elif isinstance(f, django_models.FloatField):
        ctl = ext.ExtNumberField(**kwargs)
        ctl.allow_decimals = True

    elif isinstance(f, django_models.DecimalField):
        ctl = ext.ExtNumberField(**kwargs)
        ctl.allow_decimals = True
        ctl.decimal_precision = f.decimal_places

    elif isinstance(f, (
            django_models.DateTimeField,
            django_models.DateField)):
        params = {'format': 'd.m.Y'}
        params.update(kwargs)
        ctl = ext.ExtDateField(**params)

    elif isinstance(f, django_models.TimeField):
        params = {'format': 'H:i', 'increment': 5}
        params.update(kwargs)
        ctl = ext.ExtTimeField(**params)

    elif isinstance(f, django_models.ForeignKey):
        ctl = _create_dict_select_field(f, model_register, **kwargs)

    elif isinstance(f, django_models.ImageField):
        ctl = ext.ExtImageUploadField(**kwargs)

    elif isinstance(f, django_models.FileField):
        ctl = ext.ExtFileUploadField(**kwargs)

    else:
        raise GenerationError(u'Не могу создать контрол для %s' % f)

    ctl.name = name
    ctl.label = unicode(f.verbose_name or name)
    ctl.allow_blank = f.blank

    if ctl.allow_blank and hasattr(ctl, 'hide_clear_trigger'):
        ctl.hide_clear_trigger = False

    # простановка значения по-умолчанию, если таковое указано для поля
    default = getattr(f, 'default', None)
    if default and default is not django_models.NOT_PROVIDED:
        if callable(default):
            default = default()
        ctl.value = default
        # если поле - combobox, то поставляется не только значение, но и текст
        if hasattr(ctl, 'display_field'):
            for k, v in (f.choices or []):
                if default == k:
                    ctl.default_text = v
                    break

    return ctl


def _create_dict_select_field(f, model_register=None, **kwargs):
    """
    Создает ExtDictSelectField по заданному ForeignKey-полю модели
    ActionPack предоставляется объектом :attr:`model_register` через метод
    "get", в качестве параметра принимающий имя связанной модели

    :param f: Поле модели
    :type f: django.db.models.fields.Field
    :param model_register: Реестр моделей
    :param kwargs: Параметры для передачи в конструктор ExtDictSelectField
    :type kwargs: dict
    """
    related_model = f.rel.to.__name__

    pack = (model_register or {}).get(related_model)

    assert pack, 'Cant find pack for field %s (realated model %s)' % (
        f.name, related_model)

    params = {
        'display_field': pack.column_name_on_select,
        'value_field': 'id',
        'hide_edit_trigger': True,
        'hide_trigger': getattr(pack, 'allow_paging', False),
        'hide_clear_trigger': not f.blank,
        'hide_dict_select_trigger': False,
        'editable': False,
    }
    params.update(kwargs)

    ctl = ext.ExtDictSelectField(**params)
    ctl.url = pack.get_select_url()
    ctl.pack = pack.__class__
    ctl.name = f.attname
    if not ctl.name.endswith('_id'):
        ctl.name = '%s_id' % ctl.name

    return ctl


# =============================================================================
# WindowTab
# =============================================================================
class WindowTab(object):
    """
    Прототип конструктора таба
    """
    # заголовок таба
    title = u''

    template = None  # js-шаблон для вкладки

    def _create_tab(self):
        return ext.ExtPanel(
            body_cls='x-window-mc',
            padding='5px',
            layout='form',
            title=self.title,
        )

    def init_components(self, win):
        """
        Здесь создаются компоненты, но не задаётся расположение
        Компоненты создаются, как атрибуты окна :attr:`win`

        :param win: Окно
        """
        pass

    def do_layout(self, win, tab):
        """
        Здесь задаётся расположение компонентов. Компоненты должны
        быть расположены на табе :attr:`tab` окна :attr:`win`

        :param win: Окно
        :param tab: Вкладка
        """
        pass

    def set_params(self, win, params):
        """
        Установка параметров

        :param win: Окно
        :param params: Параметры
        """
        pass


# =============================================================================
# TabbedWindow
# =============================================================================
class TabbedWindow(BaseWindow):
    """
    Окно со вкладками
    """
    # описание классов вкладок (iterable)
    tabs = None

    def _init_components(self):
        # описание вкладок должно должны быть итерабельным
        assert tools.istraversable(self.tabs), 'Wrond type of "tabs"!'

        # инстанцирование вкладок
        instantiate = lambda x: x() if inspect.isclass(x) else x
        self._tabs = map(instantiate, self.tabs or [])

        # опредение вкладок не должно быть пустым
        # (проверка производится после инстанцирования,
        # т.к. описание колонок может быть итератором
        # и иметь истинное значение в булевом контексте)
        assert self._tabs, '"tabs" can not be empty!'

        super(TabbedWindow, self)._init_components()

        # контейнер для вкладок
        self._tab_container = ext.ExtTabPanel(deferred_render=False)

        # создание компонентов для вкладок
        for con in self._tabs:
            con.init_components(win=self)

    def _do_layout(self):
        super(TabbedWindow, self)._do_layout()

        # настройка отображения окна
        self.layout = self.FIT
        self.width, self.height = 600, 450
        self.min_width, self.min_height = self.width, self.height

        self.maximizable = self.minimizable = True

        # размещение контролов во вкладках
        for con in self._tabs:
            tab = con._create_tab()
            con.do_layout(win=self, tab=tab)
            self._tab_container.items.append(tab)

        # размещение контейнера вкладок на форму
        tc = self._tab_container
        tc.anchor = '100%'
        # tc.layout = self.FIT
        tc.auto_scroll = True
        self.items.append(tc)

    def set_params(self, params):
        self.template_globals = 'tabbed-window.js'

        # установка параметров вкладок, формирование списка шаблонов вкладок
        self.tabs_templates = []
        for con in self._tabs:
            if con.template:
                self.tabs_templates.append(con.template)
            con.set_params(win=self, params=params)

        # отключение поиска в гридах во вкладках
        # т.к. рендеринг оного работает неправильно
        # TODO: найти причину
        for grid in tools.find_element_by_type(
                self._tab_container, ext.ExtObjectGrid):
            if hasattr(grid.top_bar, 'search_field'):
                grid.top_bar.search_field.hidden = True

        super(TabbedWindow, self).set_params(params)


# =============================================================================
# TabbedEditWindow
# =============================================================================
class TabbedEditWindow(TabbedWindow, BaseEditWindow):
    """
    Окно редактирования с вкладками
    """
    def _do_layout(self):
        super(TabbedEditWindow, self)._do_layout()
        self.items.remove(self._tab_container)
        self.form.items.append(self._tab_container)
        self.form.layout = self.form.FIT

        self.form.padding = None
        self._tab_container.border = False


# =============================================================================
# ObjectGridTab
# =============================================================================
class ObjectGridTab(WindowTab):
    """
    Вкладка с гридом
    """
    _pack_instance = None

    @property
    def title(self):
        """
        Заголовок вкладки
        """
        return self._pack.title

    @property
    def _pack(self):
        # кэшированная ссылка на пак
        self._pack_instance = self._pack_instance or self.get_pack()
        return self._pack_instance

    def get_pack(self):
        """
        Возвращает экземпляр ObjectPack для настройки грида
        """
        raise NotImplementedError()

    def _create_tab(self):
        tab = super(ObjectGridTab, self)._create_tab()
        tab.padding = None
        tab.layout = tab.FIT
        return tab

    def init_components(self, win):
        """
        Создание грида

        :param win: Окно
        """
        self.grid = ext.ExtObjectGrid()
        setattr(win, '%s_grid' % self.__class__.__name__, self.grid)

    def do_layout(self, win, tab):
        # помещение грида во вкладку
        tab.items.append(self.grid)

    def set_params(self, win, params):
        # настройка
        self._pack.configure_grid(self.grid)

    @classmethod
    def fabricate_from_pack(
            cls, pack_name, pack_register, tab_class_name=None):
        """
        Возвращает класс вкладки, построенной на основе
        пака с именем :attr:`pack_name`. В процессе настройки вкладки
        экземпляр пака получается посредством
        вызова :attr:`pack_register`.get_pack_instance для :attr:`pack_name`

        :param pack_name: Имя пака
        :param pack_register: Реестр паков
        :param tab_class_name: Имя класса вкладки (если не указано,
                               то генерируется на основе имени
                               класса модели пака)
        """
        tab_class_name = tab_class_name or (
            '%sTab' % pack_name.replace('/', '_'))
        return type(
            tab_class_name, (cls,),
            {'get_pack': lambda self: (
                pack_register.get_pack_instance(pack_name)
            )}
        )

    @classmethod
    def fabricate(cls, model, model_register, tab_class_name=None):
        """
        Возвращает класс вкладки, построенной на основе основного
        пака для модели :attr:`model`. В процессе настройки вкладки
        экземпляр пака получается посредством
        вызова :attr:`model_register`.get для :attr:`model_name`

        :param model: Модель django
        :type model: django.db.models.Model
        :param model_register: Реестр моделей
        :param tab_class_name: Имя класса вкладки (если не указано,
                               то генерируется на основе имени
                               класса модели пака)
        :type tab_class_name: str
        """
        tab_class_name = tab_class_name or ('%sTab' % model.__name__)
        return type(
            tab_class_name, (cls,),
            {'get_pack': lambda self: model_register.get(model.__name__)}
        )


class ObjectTab(WindowTab):
    """
    Вкладка редактирования полей объекта
    """
    # Модель, для которой будет строится окно
    model = None

    # Словарь kwargs для model_fields_to_controls ("field_list", и т.д.)
    field_fabric_params = None

    @property
    def title(self):
        """
        Заголовок вкладки
        """
        return unicode(
            self.model._meta.verbose_name or
            repr(self.model)
        )

    def init_components(self, win):
        super(ObjectTab, self).init_components(win)
        self._controls = model_fields_to_controls(
            self.model, self, **(self.field_fabric_params or {}))

    def do_layout(self, win, tab):
        super(ObjectTab, self).do_layout(win, tab)

        # автовысота вкладки
        tab.height = None
        tab.layout = 'form'
        tab.layout_config = {'autoHeight': True}

        # все поля добавляются на форму растянутыми по ширине
        tab.items.extend(map(anchor100, self._controls))

    # TODO: хз, м.б. теперь file_upload и не нужен
    # def set_params(self, win, params):
    #     super(ObjectTab, self).set_params(win, params)
    #     # если сгенерировано хотя бы одно поле загрузки файлов,
    #     # окно получает флаг разрешения загрузки файлов
    #     win.form.file_upload = win.form.file_upload or any(
    #         isinstance(x, ext.ExtFileUploadField)
    #         for x in self._controls)

    @classmethod
    def fabricate(cls, model, **kwargs):
        """
        Гененрирует класс-потомок для конкретной модели

        Использование::

            class Pack(...):
                add_window = ObjectTab.fabricate(
                    SomeModel,
                    field_list=['code', 'name'],
                    model_register=observer,
                )

        """
        return type('%sTab' % model.__name__, (cls,), {
            'model': model, 'field_fabric_params': kwargs})


# =============================================================================
# ComboBoxWithStore
# =============================================================================
class ComboBoxWithStore(ext.ExtDictSelectField):
    """
    Потомок m3-комбобокса со втроенным стором

    .. note::
        Установка артибутов data или url конфигурирует стор контрола

    """

    def __init__(self, data=None, url=None, **kwargs):
        """
        :param data: Фиксированный стор
        :type data: Iterable
        :param url: URL для загрузки
        :type url: basestring
        :param kwargs: Параметры для передачи в конструктор ExtDictSelectField
        :type kwargs: dict
        """
        super(ComboBoxWithStore, self).__init__(**kwargs)
        self.hide_trigger = False
        self.hide_clear_trigger = True
        self.hide_dict_select_trigger = True
        self._make_store(data, url)

    def _make_store(self, data=None, url=None):
        if url:
            self.store = ext_store.ExtJsonStore(url=url)
            self.store.root = 'rows'
        else:
            self.store = ext_store.ExtDataStore(data or ((0, ''),))
            self.mode = self.store.LOCAL

    @property
    def data(self):
        """
        Фиксированный стор вида ((id, name),....)
        """
        return self.store.data

    @data.setter
    def data(self, data):
        self._make_store(data=data)

    @property
    def url(self):
        """
        URL для динамической загрузки
        """
        return self.store.url

    @url.setter
    def url(self, url):
        self._make_store(url=url)


def make_combo_box(**kwargs):
    """
    Создает и возвращает ExtComboBox

    :param kwargs: Передаются в конструктор комбобокса
    :type kwargs: dict
    """
    params = dict(
        display_field='name',
        value_field='id',
        trigger_action_all=True,
        editable=False,
    )
    params.update(kwargs)
    return ComboBoxWithStore(**params)


# =============================================================================
def anchor100(ctl):
    """
    Устанавливает anchor в 100% у контрола и восвращает его (контрол)

    Пример использования::

        controls = map(anchor100, controls)

    """
    if not isinstance(ctl, django_models.DateField):
        tools.modify(ctl, anchor='100%')
    return ctl


allow_blank = lambda ctl: tools.modify(ctl, allow_blank=True)
allow_blank.__doc__ = """
    Устанавливает allow_blank=True у контрола и возвращает его (контрол)

    Пример использования::

        controls = map(allow_blank, controls)

    """

deny_blank = lambda ctl: tools.modify(ctl, allow_blank=False)
deny_blank.__doc__ = """
    Устанавливает allow_blank=False у контрола и возвращает его (контрол)

    Пример использования::

        controls = map(allow_blank, controls)

    """


# =============================================================================
# BaseMasterDetailWindow
# =============================================================================
class MasterDetailWindow(BaseWindow):
    """
    Основа для окна master-detail
    """
    _xtype = 'objectpack-master-detail-window'

    master_grid_clz = ext.ExtObjectGrid
    detail_grid_clz = ext.ExtObjectGrid

    def _init_components(self):
        self.master_grid = self.master_grid_clz()
        self.detail_grid = self.detail_grid_clz()

    def _do_layout(self):
        self.layout = 'border'
        self.master_grid.region = 'west'
        self.master_grid.width = 300
        self.detail_grid.region = 'center'
        self.items.extend([
            self.master_grid,
            self.detail_grid
        ])

    def set_params(self, params):
        super(MasterDetailWindow, self).set_params(params)
        params['master_pack'].configure_grid(self.master_grid)
        params['detail_pack'].configure_grid(self.detail_grid)
        self.master_param_name = params['master_pack'].id_param_name
        self.choose_master_msg = params.get('choose_master_msg')
