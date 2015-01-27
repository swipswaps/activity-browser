#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt4 import QtCore, QtGui, QtWebKit
# from PySide import QtCore, QtGui, QtWebKit
import sys
reload(sys)
sys.setdefaultencoding("utf-8")
from browser_utils import *
import browser_settings
import style
from mpwidget import MPWidget
import time
from ast import literal_eval
import uuid
import pprint
import multiprocessing
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt
import pickle
from random import randint


class WidgetMultiLCA(QtGui.QWidget):
    """
    A widget for performing LCA calculations for multiple datasets and multiple LCIA methods.
    """

    signal_status_bar_message = QtCore.pyqtSignal(str)
    PATH_MULTI_LCA = '.\Multi-LCA'

    def __init__(self, parent=None):
        super(WidgetMultiLCA, self).__init__(parent)
        self.lcaData = BrowserStandardTasks()
        self.helper = HelperMethods()
        self.selected_methods = []
        self.selected_activities = []
        self.results = {}

        self.set_up_ui()
        self.set_up_connections_and_context()
        self.initialize_methods_table()

    def set_up_ui(self):
        # Labels

        # Buttons
        self.button_calc_lcas = QtGui.QPushButton("Calculate")
        self.button_save_results = QtGui.QPushButton("Save results")
        self.button_load_activities = QtGui.QPushButton("Load Activities")
        self.button_save_activities = QtGui.QPushButton("Save Activities")
        self.button_load_methods = QtGui.QPushButton("Load Methods")
        self.button_save_methods = QtGui.QPushButton("Save Methods")
        # Layout buttons
        buttons_layout = QtGui.QHBoxLayout()
        buttons_layout.setAlignment(QtCore.Qt.AlignLeft)
        buttons_layout.addWidget(self.button_calc_lcas)
        buttons_layout.addWidget(self.button_save_results)
        buttons_layout.addWidget(self.button_load_activities)
        buttons_layout.addWidget(self.button_save_activities)
        buttons_layout.addWidget(self.button_load_methods)
        buttons_layout.addWidget(self.button_save_methods)

        # Tables
        self.table_activities = MyQTableWidget()
        self.table_all_methods = MyQTableWidget()
        self.table_selected_methods = MyQTableWidget()
        # Layout Tables
        VL_table_all_methods = QtGui.QVBoxLayout()
        VL_table_all_methods.addWidget(QtGui.QLabel('Available LCIA Methods (add to selection via right-click):'))
        VL_table_all_methods.addWidget(self.table_all_methods)
        widget_all_methods = QtGui.QWidget()
        widget_all_methods.setLayout(VL_table_all_methods)

        VL_table_selected_methods = QtGui.QVBoxLayout()
        VL_table_selected_methods.addWidget(QtGui.QLabel('Selected LCIA Methods (remove from selection via right-click):'))
        VL_table_selected_methods.addWidget(self.table_selected_methods)
        widget_selected_methods = QtGui.QWidget()
        widget_selected_methods.setLayout(VL_table_selected_methods)

        VL_table_activities = QtGui.QVBoxLayout()
        VL_table_activities.addWidget(QtGui.QLabel('Selected activities:'))
        VL_table_activities.addWidget(self.table_activities)
        widget_activities = QtGui.QWidget()
        widget_activities.setLayout(VL_table_activities)
        # Add tables to Splitter
        splitter = QtGui.QSplitter(QtCore.Qt.Vertical)
        splitter.addWidget(widget_all_methods)
        splitter.addWidget(widget_selected_methods)
        splitter.addWidget(widget_activities)

        # Overall layout
        vlayout = QtGui.QVBoxLayout()
        vlayout.addLayout(buttons_layout)
        vlayout.addWidget(splitter)
        self.setLayout(vlayout)

    def set_up_connections_and_context(self):
        # CONTEXT MENUS
        # Table ALL Methods
        self.table_all_methods.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.action_add_methods = QtGui.QAction(QtGui.QIcon(style.icons.context.to_multi_lca), "Add selection", None)
        self.action_add_methods.triggered.connect(self.add_selected_methods)
        self.table_all_methods.addAction(self.action_add_methods)
        # Table SELECTED Methods
        self.table_selected_methods.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.action_remove_methods = QtGui.QAction(QtGui.QIcon(style.icons.context.delete), "Remove selection", None)
        self.action_remove_methods.triggered.connect(self.remove_selected_methods)
        self.table_selected_methods.addAction(self.action_remove_methods)
        # Table ACTIVITIES
        self.table_activities.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.action_remove_activities = QtGui.QAction(QtGui.QIcon(style.icons.context.delete), "Remove selection", None)
        self.action_remove_activities.triggered.connect(self.remove_selected_activities)
        self.table_activities.addAction(self.action_remove_activities)

        # CONNECTIONS
        self.button_calc_lcas.clicked.connect(self.calculate_lcas)
        self.button_save_results.clicked.connect(self.save_results)
        self.button_load_activities.clicked.connect(self.load_activities)
        self.button_save_activities.clicked.connect(self.save_activities)
        self.button_load_methods.clicked.connect(self.load_methods)
        self.button_save_methods.clicked.connect(self.save_methods)

    def initialize_methods_table(self):
        keys = ["Family", "Category", "Subcategory"]
        methods = self.lcaData.search_methods(searchString='', length=None, does_not_contain='ecoinvent3')
        data = self.format_methods_dict(methods)
        self.table_all_methods = self.helper.update_table(self.table_all_methods, data, keys)

    def format_methods_dict(self, methods):
        data = []
        for method in methods:
            data.append({
                'Family': method[0],
                'Category': method[1] if len(method) > 1 else '',
                'Subcategory': method[2] if len(method) > 2 else '',
                'key': method,
                'key_type': 'lcia method',
            })
        data.sort(key=lambda x: x['Family'])
        return data

    def add_selected_methods(self):
        methods_to_add = [item.activity_or_database_key for item in self.table_all_methods.selectedItems()
                          if item.activity_or_database_key not in self.selected_methods]
        self.selected_methods = self.selected_methods + methods_to_add
        self.update_table_selected_methods()

    def remove_selected_methods(self):
        methods_to_remove = [item.activity_or_database_key for item in self.table_selected_methods.selectedItems()]
        for method in methods_to_remove:
            self.selected_methods.remove(method)
        self.update_table_selected_methods()

    def update_table_selected_methods(self):
        keys = ["Family", "Category", "Subcategory"]
        data = self.format_methods_dict(self.selected_methods)
        # data.sort(key=lambda x: x['Family'])
        self.table_selected_methods = self.helper.update_table(self.table_selected_methods, data, keys)

    def add_selected_activities(self, mqtw_items):
        for item in mqtw_items:
            if item.activity_or_database_key not in self.selected_activities:
                self.selected_activities.append(item.activity_or_database_key)
        self.update_table_activities()

    def remove_selected_activities(self):
        print "Activities: "
        print self.selected_activities
        for item in self.table_activities.selectedItems():
            print "removing: " + str(item.activity_or_database_key)
            self.selected_activities.remove(item.activity_or_database_key)
        self.update_table_activities()

    def update_table_activities(self):
        keys = ["product", "name", "location", "amount", "unit", "database"]
        data = [self.lcaData.getActivityData(key) for key in self.selected_activities]
        # data.sort(key=lambda x: x['name'])
        self.table_activities = self.helper.update_table(self.table_activities, data, keys)

    def load_activities(self):
        file_types = "Pickle (*.pickle);;All (*.*)"
        filepath = QtGui.QFileDialog.getOpenFileName(self, 'Open File', self.PATH_MULTI_LCA, file_types)
        try:
            with open(filepath, 'r') as infile:
                raw_data = pickle.load(infile)
        except:
            raise IOError(u'Could not load file.')
        self.selected_activities = raw_data
        self.update_table_activities()
        self.signal_status_bar_message.emit('Loaded activities from file.')

    def save_activities(self):
        file_types = "Pickle (*.pickle);;All (*.*)"
        filepath = str(QtGui.QFileDialog.getSaveFileName(self, 'Save File', self.PATH_MULTI_LCA, file_types))
        with open(filepath, 'w') as outfile:
            pickle.dump(self.selected_activities, outfile)
        self.signal_status_bar_message.emit('Saved selected activities to file.')

    def load_methods(self):
        file_types = "Pickle (*.pickle);;All (*.*)"
        filepath = QtGui.QFileDialog.getOpenFileName(self, 'Open File', self.PATH_MULTI_LCA, file_types)
        try:
            with open(filepath, 'r') as infile:
                raw_data = pickle.load(infile)
        except:
            raise IOError(u'Could not load file.')
        self.selected_methods = raw_data
        self.update_table_selected_methods()
        self.signal_status_bar_message.emit('Loaded methods from file.')

    def save_methods(self):
        file_types = "Pickle (*.pickle);;All (*.*)"
        filepath = str(QtGui.QFileDialog.getSaveFileName(self, 'Save File', self.PATH_MULTI_LCA, file_types))
        with open(filepath, 'w') as outfile:
            pickle.dump(self.selected_methods, outfile)
        self.signal_status_bar_message.emit('Saved selected methods to file.')

    def calculate_lcas(self):
        self.signal_status_bar_message.emit('Calculating...')
        tic = time.clock()
        if not self.selected_methods:
            self.signal_status_bar_message.emit('Add methods first.')
        elif not self.selected_activities:
            self.signal_status_bar_message.emit('Add activities first.')
        else:
            lca_scores, methods, activities = \
                self.lcaData.multi_lca(self.selected_activities, self.selected_methods)
            self.results.update({
                'lca_scores': lca_scores,
                'methods': methods,
                'activities': activities,
            })
            print activities
            print methods
            print lca_scores
            self.signal_status_bar_message.emit('Done in {:.2f} seconds.'.format(time.clock()-tic))

    def save_results(self):
        activity_names = [' // '.join(filter(None, [self.lcaData.getActivityData(key)['product'],
                                                    self.lcaData.getActivityData(key)['name'],
                                                    self.lcaData.getActivityData(key)['location']]))
                          for key in self.results['activities']]
        methods = [', '.join(method) for method in self.results['methods']]  # excelwrite does not support tuples
        matrix_lca_scores = self.results['lca_scores']
        file_types = "Excel (*.xlsx);;"
        filepath = str(QtGui.QFileDialog.getSaveFileName(self, 'Save File', self.PATH_MULTI_LCA, file_types))
        if filepath:
            try:
                export_matrix_to_excel(activity_names, methods, matrix_lca_scores, filepath, sheetname='Multi-LCA-Results')
                self.signal_status_bar_message.emit('Multi-LCA Results saved to: '+filepath)
            except IOError:
                self.signal_status_bar_message.emit('Could not save to file.')


class MainWindow(QtGui.QMainWindow):
    signal_add_to_chain = QtCore.pyqtSignal(MyQTableWidgetItem)
    signal_MyQTableWidgetItem = QtCore.pyqtSignal(MyQTableWidgetItem)
    signal_MyQTableWidgetItemsList = QtCore.pyqtSignal(list)
    signal_selected_text_for_clipboard = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        # tools from utils
        self.styles = Styles()
        self.helper = HelperMethods()
        self.lcaData = BrowserStandardTasks()

        # global properties
        self.cpu_count = multiprocessing.cpu_count()

        # Main Window
        self.setWindowTitle("Activity Browser")
        self.icon = QtGui.QIcon('icons/pony/pony%s.png' % str(randint(1, 7)))
        # self.icon = QtGui.QIcon('icons/activitybrowser.png')
        self.setWindowIcon(self.icon)
        self.clip = QtGui.QApplication.clipboard()

        # MAIN LAYOUT
        # H-LAYOUT -- SPLITTER -- TWO TABWIDGETS
        self.HL = QtGui.QHBoxLayout()

        self.tab_widget_LEFT = QtGui.QTabWidget()
        self.tab_widget_RIGHT = QtGui.QTabWidget()
        self.tab_widget_LEFT.setMovable(True)
        self.tab_widget_RIGHT.setMovable(True)

        self.splitter_horizontal = QtGui.QSplitter(QtCore.Qt.Horizontal)
        self.splitter_horizontal.addWidget(self.tab_widget_LEFT)
        self.splitter_horizontal.addWidget(self.tab_widget_RIGHT)
        self.HL.addWidget(self.splitter_horizontal)

        self.VL = QtGui.QVBoxLayout()
        self.VL.addLayout(self.HL)

        self.central_widget = QtGui.QWidget()
        self.central_widget.setLayout(self.VL)
        self.setCentralWidget(self.central_widget)

        # DOCKS - NOT USED HERE FOR NOW
        # dock info
        self.map_dock_name = {}
        self.map_name_dock = {}
        self.dock_info = {}
        self.areas = {}

        # EXCEPT FOR THIS BLOCK:
        # set up standard widgets in docks
        self.set_up_menu_bar()
        self.set_up_toolbar()
        self.set_up_statusbar()
        self.set_up_standard_widgets()

        # # layout docks
        # self.setDockOptions(QtGui.QMainWindow.AllowNestedDocks
        #                     | QtGui.QMainWindow.AllowTabbedDocks
        #                     | QtGui.QMainWindow.AnimatedDocks)
        # self.position_docks_at_start()
        # self.update_dock_positions()
        # # raise first tab
        # self.map_name_dock['Technosphere'].raise_()
        # self.map_name_dock['Databases'].raise_()
        # self.setTabPosition(QtCore.Qt.LeftDockWidgetArea, QtGui.QTabWidget.North)
        # self.setTabPosition(QtCore.Qt.RightDockWidgetArea, QtGui.QTabWidget.North)

        # at program start
        self.listDatabases()

    # Setup of UIs, connections...

    def set_up_standard_widgets(self):
        self.set_up_widget_databases()
        self.set_up_widget_technosphere()
        self.set_up_widget_biosphere()
        self.set_up_widget_search()
        self.set_up_widget_LCIA()
        self.set_up_widget_LCA_results()
        self.setup_widget_activity_editor()

        # FROM OUTSIDE CLASSES
        # Widget Multi-LCA
        self.widget_multi_lca = WidgetMultiLCA()
        self.tab_widget_LEFT.addTab(self.widget_multi_lca, 'Multi-LCA')
        self.signal_MyQTableWidgetItemsList.connect(self.widget_multi_lca.add_selected_activities)
        self.widget_multi_lca.signal_status_bar_message.connect(self.statusBarMessage)

        self.set_up_additional_context_menus()

        # enable COPY from tables
        tables = [
            self.table_databases,
            self.table_inputs_technosphere,
            self.table_current_activity,
            self.table_downstream_activities,
            self.table_search,
            self.table_inputs_biosphere,
            self.table_current_activity_lcia,
            self.table_AE_biosphere,
            self.table_AE_technosphere,
            self.table_AE_activity,
            self.table_lcia_results,
            self.table_previous_calcs,
            self.table_top_emissions,
            self.table_top_processes,
        ]
        tables_multi_lca = [
            self.widget_multi_lca.table_all_methods,
            self.widget_multi_lca.table_selected_methods,
            self.widget_multi_lca.table_activities,
        ]
        for table in tables + tables_multi_lca:
            table.signal_copy_selected_text.connect(self.set_clipboard_text)

    def set_up_menu_bar(self):
        # EXTENSIONS
        extensions_menu = QtGui.QMenu('&Extensions', self)

        addMP = QtGui.QAction(QtGui.QIcon('icons/metaprocess/metaprocess.png'), '&Meta-Process Editor', self)
        addMP.setShortcut('Ctrl+E')
        addMP.setStatusTip('Start Meta-Process Editor')
        addMP.triggered.connect(self.set_up_widgets_meta_process)

        extensions_menu.addAction(addMP)

        # HELP
        help_menu = QtGui.QMenu('&Help', self)
        help_menu.addAction(self.icon, '&About Activity Browser', self.about)
        help_menu.addAction('&About Qt', self.about_qt)

        # ::: MENU BAR :::
        self.menubar = QtGui.QMenuBar()
        # self.menubar = self.menuBar()
        self.menubar.addMenu(extensions_menu)
        self.menubar.addMenu(help_menu)
        self.setMenuBar(self.menubar)

    def set_up_toolbar(self):
        # free icons from http://www.flaticon.com/search/history

        # Search line edits
        self.line_edit_search = QtGui.QLineEdit()
        self.line_edit_search.setMaximumSize(QtCore.QSize(150, 25))
        self.line_edit_search_1 = QtGui.QLineEdit()
        self.line_edit_search_1.setMaximumSize(QtCore.QSize(150, 25))

        # Search
        action_search = QtGui.QAction(QtGui.QIcon('icons/search.png'), 'Search activites (blank: all activities)', self)
        # action_search.setShortcut('Ctrl+Q')
        # action_search.setToolTip('Search activites (blank: all activities)')
        action_search.triggered.connect(self.search_results)

        # Key
        action_key = QtGui.QAction(QtGui.QIcon('icons/key.png'), 'Search by key', self)
        action_key.triggered.connect(self.search_by_key)

        # Random activity
        action_random_activity = QtGui.QAction(QtGui.QIcon('icons/random_activity.png'), 'Load a random activity', self)
        action_random_activity.triggered.connect(lambda: self.load_new_current_activity())

        # History
        action_history = QtGui.QAction(QtGui.QIcon('icons/history.png'), 'Previously visited activities', self)
        action_history.triggered.connect(self.showHistory)

        # Backward
        action_backward = QtGui.QAction(QtGui.QIcon('icons/backward.png'), 'Go backward', self)
        action_backward.setShortcut('Alt+left')
        action_backward.triggered.connect(self.goBackward)

        # Forward
        action_forward = QtGui.QAction(QtGui.QIcon('icons/forward.png'), 'Go forward', self)
        action_forward.setShortcut('Alt+right')
        action_forward.triggered.connect(self.goForward)

        # Edit
        action_edit = QtGui.QAction(QtGui.QIcon('icons/edit.png'), 'Edit activity', self)
        action_edit.triggered.connect(self.edit_activity)

        # Calculate
        action_calculate = QtGui.QAction(QtGui.QIcon('icons/calculate.png'),
                                       'Calculate LCA (with settings in LCIA tab)', self)
        action_calculate.triggered.connect(self.calculate_lcia)

        # toolbar
        self.toolbar = QtGui.QToolBar('Toolbar')
        self.toolbar.addWidget(self.line_edit_search)
        self.toolbar.addSeparator()
        self.toolbar.addWidget(self.line_edit_search_1)
        self.toolbar.addAction(action_search)
        self.toolbar.addAction(action_key)
        self.toolbar.addAction(action_random_activity)
        self.toolbar.addAction(action_history)
        self.toolbar.addAction(action_backward)
        self.toolbar.addAction(action_forward)
        self.toolbar.addAction(action_edit)
        self.toolbar.addAction(action_calculate)
        self.addToolBar(self.toolbar)

        # Connections
        self.line_edit_search.returnPressed.connect(self.search_results)
        self.line_edit_search_1.returnPressed.connect(self.search_results)

    def set_up_statusbar(self):
        self.statusbar = QtGui.QStatusBar()
        self.setStatusBar(self.statusbar)

        self.status_message = QtGui.QLabel('Welcome')
        self.status_database = QtGui.QLabel('Database')

        self.statusbar.addWidget(self.status_message, 1)
        self.statusbar.addWidget(self.status_database, 0)
        # self.status_message.setText("Welcome")

    def set_up_widget_technosphere(self):
        # LABELS
        # dynamic
        self.label_current_activity_product = QtGui.QLabel("Product")
        self.label_current_activity_product.setFont(self.styles.font_big)
        self.label_current_activity_product.setStyleSheet("QLabel { color : blue; }")
        self.label_current_activity = QtGui.QLabel("Activity Name")
        self.label_current_activity.setFont(self.styles.font_big)
        self.label_current_database = QtGui.QLabel("Database")
        # static
        label_inputs = QtGui.QLabel("Technosphere Inputs")
        label_current_activity = QtGui.QLabel("Current Activity")
        # label_current_activity.setFont(self.styles.font_bold)
        label_downstream_activities = QtGui.QLabel("Downstream Activities")

        # Tables
        self.table_inputs_technosphere = MyQTableWidget()
        self.table_current_activity = MyQTableWidget()
        self.table_downstream_activities = MyQTableWidget()
        self.table_inputs_technosphere.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.table_current_activity.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.table_downstream_activities.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)

        # Current Activity
        # VL_activity_info = QtGui.QVBoxLayout()
        # VL_activity_info.setAlignment(QtCore.Qt.AlignLeft)
        # VL_activity_info.addWidget(self.label_current_activity_product)
        # VL_activity_info.addWidget(self.label_current_activity)
        # VL_activity_info.addWidget(self.label_current_database)
        # frame = QtGui.QFrame()
        # frame.setLayout(VL_activity_info)
        # Layout
        VL_technosphere = QtGui.QVBoxLayout()
        VL_technosphere.addWidget(label_inputs)
        VL_technosphere.addWidget(self.table_inputs_technosphere)
        VL_technosphere.addWidget(label_current_activity)
        VL_technosphere.addWidget(self.table_current_activity)
        # VL_technosphere.addWidget(frame)
        VL_technosphere.addWidget(label_downstream_activities)
        VL_technosphere.addWidget(self.table_downstream_activities)
        widget_technosphere = QtGui.QWidget()
        widget_technosphere.setLayout(VL_technosphere)
        # dock
        # self.add_dock(widget_technosphere, 'Technosphere', QtCore.Qt.RightDockWidgetArea)

        # Connections
        self.table_inputs_technosphere.itemDoubleClicked.connect(self.gotoDoubleClickActivity)
        self.table_downstream_activities.itemDoubleClicked.connect(self.gotoDoubleClickActivity)

        self.tab_widget_LEFT.addTab(widget_technosphere, 'Technosphere')

    def set_up_widget_databases(self):
        button_add_db = QtGui.QPushButton('New Database')
        button_refresh = QtGui.QPushButton('Refresh')
        # Layout buttons
        buttons_layout = QtGui.QHBoxLayout()
        buttons_layout.setAlignment(QtCore.Qt.AlignLeft)
        buttons_layout.addWidget(button_add_db)
        buttons_layout.addWidget(button_refresh)
        # Table
        self.table_databases = MyQTableWidget()
        # Overall Layout
        VL_database_tab = QtGui.QVBoxLayout()
        VL_database_tab.addWidget(self.table_databases)
        VL_database_tab.addLayout(buttons_layout)
        widget_databases = QtGui.QWidget()
        widget_databases.setLayout(VL_database_tab)
        # self.add_dock(self.table_databases, 'Databases', QtCore.Qt.LeftDockWidgetArea)

        # Context menus
        self.table_databases.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)

        self.action_delete_database = QtGui.QAction(QtGui.QIcon(style.icons.context.delete), "delete database", None)
        self.action_delete_database.triggered.connect(self.delete_database)
        self.table_databases.addAction(self.action_delete_database)

        # Connections
        self.table_databases.itemDoubleClicked.connect(self.gotoDoubleClickDatabase)
        button_add_db.clicked.connect(self.new_database)
        button_refresh.clicked.connect(self.listDatabases)

        self.tab_widget_RIGHT.addTab(widget_databases, 'Databases')

    def set_up_widget_search(self):
        self.label_multi_purpose = QtGui.QLabel()
        self.table_search = MyQTableWidget()
        self.table_search.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        # Layout
        vl = QtGui.QVBoxLayout()
        vl.addWidget(self.label_multi_purpose)
        vl.addWidget(self.table_search)
        # dock
        self.widget_search = QtGui.QWidget()
        self.widget_search.setLayout(vl)
        # self.add_dock(widget, 'Search', QtCore.Qt.RightDockWidgetArea)

        # CONTEXT MENUS
        self.action_delete_activity = QtGui.QAction(QtGui.QIcon(style.icons.context.delete), "delete activity", None)
        self.action_delete_activity.triggered.connect(self.delete_activity)
        self.table_search.addAction(self.action_delete_activity)

        # Connections
        self.table_search.itemDoubleClicked.connect(self.gotoDoubleClickActivity)

        self.tab_widget_RIGHT.addTab(self.widget_search, 'Search')

    def set_up_widget_biosphere(self):
        self.table_inputs_biosphere = MyQTableWidget()
        self.table_inputs_biosphere.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        # self.add_dock(self.table_inputs_biosphere, 'Biosphere', QtCore.Qt.RightDockWidgetArea)

        self.tab_widget_RIGHT.addTab(self.table_inputs_biosphere, 'Biosphere')

    def set_up_widget_LCIA(self):
        # Labels
        self.label_LCIAW_functional_unit = QtGui.QLabel("Functional Unit:")
        label_lcia_method = QtGui.QLabel("LCIA method:")
        label_previous_calcs = QtGui.QLabel("Previous calculations")
        # Line edits
        self.line_edit_monte_carlo_iterations = QtGui.QLineEdit("100")
        self.line_edit_monte_carlo_iterations.setMaximumSize(QtCore.QSize(40, 30))
        # Buttons
        self.button_clear_lcia_methods = QtGui.QPushButton("Clear Method")
        self.button_calc_lcia = QtGui.QPushButton("Calculate")
        self.button_calc_monte_carlo = QtGui.QPushButton("Monte Carlo")
        # Dropdown
        self.combo_lcia_method_part0 = QtGui.QComboBox(self)
        self.combo_lcia_method_part1 = QtGui.QComboBox(self)
        self.combo_lcia_method_part2 = QtGui.QComboBox(self)
        # Tables
        self.table_current_activity_lcia = MyQTableWidget()
        self.table_previous_calcs = MyQTableWidget()

        # set default LCIA method
        self.update_lcia_method(selection=browser_settings.default_LCIA_method)

        # MATPLOTLIB FIGURE Monte Carlo
        self.matplotlib_figure_mc = QtGui.QWidget()
        self.figure_mc = plt.figure()
        self.canvas_mc = FigureCanvas(self.figure_mc)
        self.toolbar_mc = NavigationToolbar(self.canvas_mc, self.matplotlib_figure_mc)

        # set the layout
        plt_layout = QtGui.QVBoxLayout()
        plt_layout.addWidget(self.toolbar_mc)
        plt_layout.addWidget(self.canvas_mc)
        self.matplotlib_figure_mc.setLayout(plt_layout)

        # HL
        HL_buttons_lcia = QtGui.QHBoxLayout()
        HL_buttons_lcia.setAlignment(QtCore.Qt.AlignLeft)
        HL_buttons_lcia.addWidget(self.button_calc_lcia)
        HL_buttons_lcia.addWidget(self.button_calc_monte_carlo)
        HL_buttons_lcia.addWidget(self.line_edit_monte_carlo_iterations)

        HL_LCIA = QtGui.QHBoxLayout()
        HL_LCIA.setAlignment(QtCore.Qt.AlignLeft)
        HL_LCIA.addWidget(label_lcia_method)
        HL_LCIA.addWidget(self.button_clear_lcia_methods)

        # VL
        self.VL_LCIA_widget = QtGui.QVBoxLayout()
        self.VL_LCIA_widget.addLayout(HL_buttons_lcia)
        self.VL_LCIA_widget.addWidget(self.label_LCIAW_functional_unit)
        self.VL_LCIA_widget.addWidget(self.table_current_activity_lcia)
        self.VL_LCIA_widget.addLayout(HL_LCIA)
        self.VL_LCIA_widget.addWidget(self.combo_lcia_method_part0)
        self.VL_LCIA_widget.addWidget(self.combo_lcia_method_part1)
        self.VL_LCIA_widget.addWidget(self.combo_lcia_method_part2)
        self.VL_LCIA_widget.addWidget(label_previous_calcs)
        self.VL_LCIA_widget.addWidget(self.table_previous_calcs)
        self.VL_LCIA_widget.addWidget(self.matplotlib_figure_mc)
        # dock
        self.widget_LCIA = QtGui.QWidget()
        self.widget_LCIA.setLayout(self.VL_LCIA_widget)
        # self.add_dock(self.widget_LCIA, 'LCIA', QtCore.Qt.LeftDockWidgetArea)
        # Connections
        self.button_calc_lcia.clicked.connect(self.calculate_lcia)
        self.button_calc_monte_carlo.clicked.connect(self.calculate_monte_carlo)
        self.table_previous_calcs.itemDoubleClicked.connect(self.load_previous_LCA_results)
        self.combo_lcia_method_part0.currentIndexChanged.connect(self.update_lcia_method)
        self.combo_lcia_method_part1.currentIndexChanged.connect(self.update_lcia_method)
        self.combo_lcia_method_part2.currentIndexChanged.connect(self.update_lcia_method)
        self.button_clear_lcia_methods.clicked.connect(lambda: self.update_lcia_method(selection=('', '', '')))
        self.table_current_activity_lcia.itemChanged.connect(self.update_functional_unit)

        self.tab_widget_LEFT.addTab(self.widget_LCIA, 'LCIA')

    def set_up_widget_LCA_results(self):
        # Labels
        self.label_LCAR_product = QtGui.QLabel("Product")
        self.label_LCAR_product.setFont(self.styles.font_bold)
        self.label_LCAR_product.setStyleSheet("QLabel { color : blue; }")
        self.label_LCAR_activity = QtGui.QLabel("Activity")
        self.label_LCAR_activity.setFont(self.styles.font_bold)
        self.label_LCAR_database = QtGui.QLabel("Database")
        self.label_LCAR_fu = QtGui.QLabel("Functional Unit")
        self.label_LCAR_method = QtGui.QLabel("Method")
        self.label_LCAR_score = QtGui.QLabel("LCA score")
        self.label_LCAR_score.setFont(self.styles.font_bold)
        self.label_LCAR_score.setStyleSheet("QLabel { color : red; }")
        label_top_processes = QtGui.QLabel("Top Processes")
        label_top_emissions = QtGui.QLabel("Top Emissions")
        # Tables
        self.table_lcia_results = MyQTableWidget()
        self.table_top_processes = MyQTableWidget()
        self.table_top_emissions = MyQTableWidget()
        # VL
        VL_widget_LCIA_Results = QtGui.QVBoxLayout()
        VL_widget_LCIA_Results.addWidget(self.label_LCAR_product)
        VL_widget_LCIA_Results.addWidget(self.label_LCAR_activity)
        VL_widget_LCIA_Results.addWidget(self.label_LCAR_database)
        VL_widget_LCIA_Results.addWidget(self.label_LCAR_fu)
        VL_widget_LCIA_Results.addWidget(self.label_LCAR_method)
        VL_widget_LCIA_Results.addWidget(self.label_LCAR_score)
        VL_widget_LCIA_Results.addWidget(label_top_processes)
        VL_widget_LCIA_Results.addWidget(self.table_top_processes)
        VL_widget_LCIA_Results.addWidget(label_top_emissions)
        VL_widget_LCIA_Results.addWidget(self.table_top_emissions)
        # dock
        self.widget_LCIA_Results = QtGui.QWidget()
        self.widget_LCIA_Results.setLayout(VL_widget_LCIA_Results)
        # self.add_dock(widget_LCIA_Results, 'LCA Results', QtCore.Qt.RightDockWidgetArea)
        # Connections

        self.tab_widget_RIGHT.addTab(self.widget_LCIA_Results, 'LCA Results')

    def setup_widget_activity_editor(self):
        # Labels
        self.label_ae_activity = QtGui.QLabel("Activity")
        self.label_ae_database = QtGui.QLabel("Select database")
        self.label_ae_tech_in = QtGui.QLabel("Technosphere Inputs")
        self.label_ae_bio_in = QtGui.QLabel("Biosphere Inputs")
        # Buttons
        self.button_save = QtGui.QPushButton("Save New Activity")
        self.button_replace = QtGui.QPushButton("Replace Existing")
        # TABLES
        self.table_AE_activity = MyQTableWidget()
        self.table_AE_technosphere = MyQTableWidget()
        self.table_AE_biosphere = MyQTableWidget()
        self.table_AE_technosphere.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.table_AE_biosphere.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        # Dropdown
        self.combo_databases = QtGui.QComboBox(self)
        self.update_read_and_write_database_list()
        # HL
        HL_AE_actions = QtGui.QHBoxLayout()
        HL_AE_actions.addWidget(self.label_ae_database)
        HL_AE_actions.addWidget(self.combo_databases)
        HL_AE_actions.addWidget(self.button_save)
        HL_AE_actions.addWidget(self.button_replace)
        HL_AE_actions.setAlignment(QtCore.Qt.AlignLeft)
        # VL
        VL_AE = QtGui.QVBoxLayout()
        VL_AE.addWidget(self.label_ae_activity)
        VL_AE.addWidget(self.table_AE_activity)
        VL_AE.addWidget(self.label_ae_tech_in)
        VL_AE.addWidget(self.table_AE_technosphere)
        VL_AE.addWidget(self.label_ae_bio_in)
        VL_AE.addWidget(self.table_AE_biosphere)
        VL_AE.addLayout(HL_AE_actions)
        # AE widget
        # dock
        self.widget_AE = QtGui.QWidget()
        self.widget_AE.setLayout(VL_AE)
        # self.add_dock(widget_AE, 'Activity Editor', QtCore.Qt.RightDockWidgetArea)

        # Connections
        self.table_AE_technosphere.itemDoubleClicked.connect(self.gotoDoubleClickActivity)
        self.table_AE_activity.itemChanged.connect(self.change_values_activity)
        self.table_AE_technosphere.itemChanged.connect(
            lambda: self.change_exchange_values(self.table_AE_technosphere.currentItem()))
        self.table_AE_biosphere.itemChanged.connect(
            lambda: self.change_exchange_values(self.table_AE_biosphere.currentItem()))
        self.button_save.clicked.connect(self.save_edited_activity)
        self.button_replace.clicked.connect(self.replace_edited_activity)

        # CONTEXT MENUS
        tables = [
            self.table_inputs_technosphere,
            self.table_inputs_biosphere,
            self.table_downstream_activities,
            self.table_search
        ]
        # action add exchanges
        for table in tables:
            action = QtGui.QAction(QtGui.QIcon(style.icons.context.to_edited_activity), "to edited activity", table)
            action.triggered[()].connect(lambda table=table: self.add_exchange_to_edited_activity(table.selectedItems()))
            table.addAction(action)

        # action remove exchanges
        for table in [self.table_AE_technosphere, self.table_AE_biosphere]:
            action = QtGui.QAction(QtGui.QIcon(style.icons.context.delete), "remove", table)
            action.triggered[()].connect(lambda table=table: self.remove_exchange_from_edited_activity(table.selectedItems()))
            table.addAction(action)

        self.tab_widget_RIGHT.addTab(self.widget_AE, 'Activity Editor')

    def set_up_additional_context_menus(self):
        # action add activities to Multi-LCA
        tables = [
            self.table_inputs_technosphere,
            self.table_current_activity,
            self.table_downstream_activities,
            self.table_search
        ]
        for table in tables:
            action = QtGui.QAction(QtGui.QIcon(style.icons.context.to_multi_lca), "to Multi-LCA", table)
            action.triggered[()].connect(lambda table=table: self.add_to_multi_lca(table.selectedItems()))
            table.addAction(action)

    def about(self):
        text="""
Activity Browser

Copyright 2015 Bernhard Steubing, ETH Zurich

Contact: steubing@ifu.baug.ethz.ch

The Activity Browser is an LCA software based on
brightway2: http://brightwaylca.org/

The Activity Browser may *not* be used or modified
without prior consent of the author. Copies of
the software may *not* be distributed without
the author's written consent."""

        # QtGui.QMessageBox.about(self, "About", text)

        msgBox = QtGui.QMessageBox()
        msgBox.setWindowTitle('About the Activity Browser')
        pixmap = self.icon.pixmap(QtCore.QSize(150, 150))
        msgBox.setIconPixmap(pixmap)
        msgBox.setWindowIcon(self.icon)
        msgBox.setText(text)
        msgBox.exec_()

    def about_qt(self):
        QtGui.QMessageBox.aboutQt(self)

    def statusBarMessage(self, message):
        """
        Can be used to display status bar messages from other widgets via signal-connect.
        :param message:
        :return:
        """
        self.status_message.setText(message)

    # SIGNAL-SLOT METHODS
    def add_to_multi_lca(self, selectedItems):
        self.signal_MyQTableWidgetItemsList.emit(selectedItems)

    @QtCore.pyqtSlot(str)
    def set_clipboard_text(self, clipboard_text):
        print "Received:\n", clipboard_text
        self.clip.setText(clipboard_text)

    # META-PROCESS STUFF

    def set_up_widgets_meta_process(self):
        if hasattr(self, 'MP_Widget'):
            print "MP WIDGET ALREADY LOADED"
        else:
            self.MP_Widget = MPWidget()
            self.tab_widget_LEFT.addTab(self.MP_Widget.MPdataWidget, "MP")
            # self.add_dock(self.MP_Widget.MPdataWidget, 'MP', QtCore.Qt.LeftDockWidgetArea)
            self.tab_widget_LEFT.addTab(self.MP_Widget.table_MP_database, "MP database")
            # self.add_dock(self.MP_Widget.table_MP_database, 'MP database', QtCore.Qt.LeftDockWidgetArea)
            self.tab_widget_LEFT.addTab(self.MP_Widget.PP_analyzer, "MP LCA")
            # self.add_dock(self.MP_Widget.PP_analyzer, 'MP LCA', QtCore.Qt.LeftDockWidgetArea)
            # self.VL_LEFT.addLayout(self.MP_Widget.HL_MP_buttons)
            # self.VL_LEFT.addLayout(self.MP_Widget.HL_MP_Database_buttons)

            # toolbar
            self.toolbar_MP = QtGui.QToolBar()
            self.addToolBar(self.MP_Widget.toolbar)

            # vl = QtGui.QVBoxLayout()
            # vl.addLayout(self.MP_Widget.HL_MP_buttons)
            # vl.addLayout(self.MP_Widget.HL_MP_Database_buttons)
            # widget = QtGui.QWidget()
            # widget.setLayout(vl)
            # self.add_dock(widget, 'buttons', QtCore.Qt.LeftDockWidgetArea)

            self.tab_widget_RIGHT.addTab(self.MP_Widget.webview, "Graph")
            # self.add_dock(self.MP_Widget.webview, 'Graph', QtCore.Qt.RightDockWidgetArea)
            # self.webview = QtWebKit.QWebView()
            # self.setCentralWidget(self.webview)
            # self.tab_widget_RIGHT.addTab(self.webview, "Graph")
            # self.tab_widget_RIGHT.addTab(QtGui.QWidget(), "Graph")
            # self.position_docks_at_start()
            # self.update_dock_positions()
            # print self.map_name_dock.keys()
            # print self.areas
            # print self.dock_info

            # CONTEXT MENUS
            tables = [
                self.table_current_activity,
                self.table_inputs_technosphere,
                self.table_downstream_activities,
                self.table_search
            ]
            for table in tables:
                action = QtGui.QAction(QtGui.QIcon(style.icons.mp.metaprocess), "to Meta-Process", table)
                action.triggered[()].connect(lambda table=table: self.add_to_chain(table.selectedItems()))
                table.addAction(action)

            # CONNECTIONS BETWEEN WIDGETS
            self.signal_add_to_chain.connect(self.MP_Widget.addToChain)
            self.MP_Widget.signal_MyQTableWidgetItem.connect(self.gotoDoubleClickActivity)
            self.MP_Widget.signal_status_bar_message.connect(self.statusBarMessage)

            # copy
            tables_mp = [
                self.MP_Widget.table_MP_database,
                self.MP_Widget.table_MP_chain,
                self.MP_Widget.table_MP_outputs,
                self.MP_Widget.table_PP_comparison
            ]
            for table in tables_mp:
                table.signal_copy_selected_text.connect(self.set_clipboard_text)

            # MENU BAR
            # # Actions
            # exportMPDatabaseAsJSONFile = QtGui.QAction('Export DB to file', self)
            # exportMPDatabaseAsJSONFile.setStatusTip('Export the working MP database as JSON to a .py file')
            # self.connect(exportMPDatabaseAsJSONFile, QtCore.SIGNAL('triggered()'), self.MP_Widget.export_as_JSON)
            # # Add actions
            # # menubar = self.menuBar()
            #
            # mp_menu = self.menubar.addMenu('MP')
            # mp_menu.addAction(exportMPDatabaseAsJSONFile)

    def add_to_chain(self, items):
        for item in items:
            self.signal_add_to_chain.emit(item)

    # NAVIGATION

    def gotoDoubleClickActivity(self, item):
        print "DOUBLECLICK on: ", item.text()
        if item.key_type == "activity":
            print "Loading Activity:", item.activity_or_database_key
            self.load_new_current_activity(item.activity_or_database_key)

    def load_new_current_activity(self, key=None, mode=None):

        if not self.lcaData.db:
            self.status_message.setText("Load a database first")
        else:
            if not mode:
                self.lcaData.setNewCurrentActivity(key, record=True)
            elif mode == 'backward':
                self.lcaData.go_backward()
            elif mode == 'forward':
                self.lcaData.go_forward()

            ad = self.lcaData.getActivityData()
            keys = self.get_table_headers()
            # current activity table
            self.table_current_activity = self.format_table_current_activity(
                self.table_current_activity, keys, ad)
            self.table_current_activity_lcia = self.format_table_current_activity(
                self.table_current_activity_lcia, keys, ad, edit_keys='amount')
            # other tables
            self.table_inputs_technosphere = self.helper.update_table(self.table_inputs_technosphere, self.lcaData.get_exchanges(type="technosphere"), keys)
            self.table_inputs_biosphere = self.helper.update_table(self.table_inputs_biosphere, self.lcaData.get_exchanges(type="biosphere"), self.get_table_headers(type="biosphere"))
            self.table_downstream_activities = self.helper.update_table(self.table_downstream_activities, self.lcaData.get_downstream_exchanges(), keys)

            # self.status_database.setText(ad['database'])
            self.status_database.setText(self.lcaData.db.name)

    def format_table_current_activity(self, table, keys, ad, edit_keys=None):
        table = self.helper.update_table(table, [ad], keys, bold=True, edit_keys=edit_keys)
        table.setMaximumHeight(
            # btable.horizontalHeader().height()
            + table.rowHeight(0)
            + table.autoScrollMargin()
        )
        table.setShowGrid(False)
        table.horizontalHeader().hide()
        table.verticalHeader().hide()

        table.setStyleSheet(style.stylesheet_current_activity)

        return table

    def showHistory(self):
        keys = self.get_table_headers(type="history")
        data = self.lcaData.getHistory()
        self.table_search = self.helper.update_table(self.table_search, data, keys)
        label_text = "History"
        self.label_multi_purpose.setText(QtCore.QString(label_text))
        self.tab_widget_RIGHT.setCurrentIndex(self.tab_widget_RIGHT.indexOf(self.widget_search))

    def goBackward(self):
        if self.lcaData.backward_options:
            self.load_new_current_activity(mode='backward')
        else:
            self.status_message.setText("Cannot go further back.")

    def goForward(self):
        if self.lcaData.forward_options:
            self.load_new_current_activity(mode='forward')
        else:
            self.status_message.setText("Cannot go forward.")

    def get_table_headers(self, type="technosphere"):
        if self.lcaData.database_version == 2:
            if type == "technosphere":
                # keys = ["name", "location", "amount", "unit", "database"]
                keys = ["amount", "unit", "name", "location", "database"]
            elif type == "biosphere":
                keys = ["name", "amount", "unit"]
            elif type == "history" or type == "search":
                keys = ["name", "location", "unit", "database", "key"]
        else:
            if type == "technosphere":
                # keys = ["product", "name", "location", "amount", "unit", "database"]
                keys = ["amount", "unit", "product", "name", "location", "database"]
            elif type == "biosphere":
                keys = ["name", "amount", "unit"]
            elif type == "history" or type == "search":
                keys = ["product", "name", "location", "unit", "database", "key"]
        return keys

    # DATABASES

    def listDatabases(self):
        data = self.lcaData.getDatabases()
        keys = ["name", "activities", "dependencies"]
        self.table_databases = self.helper.update_table(self.table_databases, data, keys)
        self.tab_widget_RIGHT.setCurrentIndex(self.tab_widget_RIGHT.indexOf(self.table_databases))
        self.update_read_and_write_database_list()

    def gotoDoubleClickDatabase(self, item):
        print "DOUBLECLICK on: ", item.text()
        if item.key_type != "activity":
            tic = time.clock()
            self.status_message.setText("Loading... "+item.activity_or_database_key)
            print "Loading Database:", item.activity_or_database_key
            self.lcaData.loadDatabase(item.activity_or_database_key)
            self.status_message.setText(str("Database loaded: {0} in {1:.2f} seconds.").format(item.activity_or_database_key, (time.clock()-tic)))
        self.status_database.setText(self.lcaData.db.name)

    def new_database(self):
        name, ok = QtGui.QInputDialog.getText(self, 'Input Dialog',
            'Please enter a database name:')
        if ok:
            if name in self.lcaData.list_databases():
                self.status_message.setText('The name you have specified already exists. Please choose another name.')
            else:
                self.lcaData.add_database(str(name), data={})
                self.status_message.setText("Created new database: %s" % name)
                self.listDatabases()

    def delete_database(self):
        item = self.table_databases.currentItem()
        msg = "You are about to delete the database: \n%s \nAre you sure you want to continue?" % item.activity_or_database_key
        reply = QtGui.QMessageBox.question(self, 'Message',
            msg, QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
        if reply:
            try:
                self.lcaData.delete_database(item.activity_or_database_key)
                self.status_message.setText("Deleted "+item.activity_or_database_key)
                self.listDatabases()
            except:
                self.status_message.setText("An error must have occured. Could not delete database.")

    # SEARCH

    def search_results(self):
        searchString1 = str(self.line_edit_search.text())
        searchString2 = str(self.line_edit_search_1.text())
        self.status_message.setText("Searched for "+' + '.join(filter(None, [searchString1, searchString2])))
        if self.lcaData.db:
            data = self.lcaData.multi_search_activities(searchString1, searchString2)
            keys = self.get_table_headers(type="search")
            self.table_search = self.helper.update_table(self.table_search, data, keys)
            label_text = str(len(data)) + " activities found."
            self.label_multi_purpose.setText(QtCore.QString(label_text))
            self.tab_widget_RIGHT.setCurrentIndex(self.tab_widget_RIGHT.indexOf(self.widget_search))
        else:
            self.status_message.setText("Load a database first")

    def search_by_key(self):
        searchString = str(self.line_edit_search.text())
        try:
            if searchString != '':
                print "\nSearched for:", searchString
                data = [self.lcaData.getActivityData(literal_eval(searchString))]
                print "Data: "
                print data
                keys = self.get_table_headers(type="search")
                self.table_search = self.helper.update_table(self.table_search, data, keys)
                label_text = str(len(data)) + " activities found."
                self.label_multi_purpose.setText(QtCore.QString(label_text))
                self.tab_widget_RIGHT.setCurrentIndex(self.tab_widget_RIGHT.indexOf(self.widget_search))
        except AttributeError:
            self.status_message.setText("Load a database first")
        except:
            self.status_message.setText("Cannot find activity key for this.")

    # LCIA and LCA Results

    def update_functional_unit(self):
        keys = self.get_table_headers()
        ad = self.lcaData.getActivityData()
        item = self.table_current_activity_lcia.currentItem()
        value = item.text()
        if self.helper.is_float(value):
            ad['amount'] = float(value)
        # update current activity table lcia
        self.table_current_activity_lcia = self.format_table_current_activity(
            self.table_current_activity_lcia, keys, ad, edit_keys='amount')

    def update_lcia_method(self, current_index=0, selection=None):
        if not selection:
            selection = (str(self.combo_lcia_method_part0.currentText()), str(self.combo_lcia_method_part1.currentText()), str(self.combo_lcia_method_part2.currentText()))
            print "LCIA method combobox selection: "+str(selection)
        methods, parts = self.lcaData.get_selectable_LCIA_methods(selection)
        # set new available choices
        comboboxes = [self.combo_lcia_method_part0, self.combo_lcia_method_part1, self.combo_lcia_method_part2]
        for i, combo in enumerate(comboboxes):
            combo.blockSignals(True)
            combo.clear()
            combo.addItems(['']+parts[i])
            if len(parts[i]) == 1:  # choice made for this combobox (and then only 2 left: 0='', 1='choice'
                combo.setCurrentIndex(1)
            combo.blockSignals(False)

    def calculate_lcia(self, monte_carlo=False):
        method = self.lcaData.LCIA_METHOD
        if not self.lcaData.currentActivity:
            self.status_message.setText("Load an activity first.")
        elif not method:
            self.status_message.setText("Select an LCIA method first.")
        else:
            item = self.helper.get_table_item(self.table_current_activity_lcia, 0, 'amount')
            if self.helper.is_float(item.text()):
                amount = float(item.text())
                print "amount of functional unit: ", amount
            else:
                amount = 1.0
            tic = time.clock()
            # Standard LCA
            uuid_ = self.lcaData.lcia(amount=amount, method=method)
            # Monte Carlo LCA
            if self.helper.is_int(self.line_edit_monte_carlo_iterations.text()):
                self.mc_iterations = int(self.line_edit_monte_carlo_iterations.text())
            else:
                self.mc_iterations = 100
            if monte_carlo:
                self.lcaData.monte_carlo_lcia(key=None, amount=amount, method=method,
                                              iterations=self.mc_iterations, cpu_count=self.cpu_count, uuid_=uuid_)
            self.status_message.setText("Calculated LCIA score in {:.2f} seconds.".format(time.clock()-tic))
            # Update Table Previous LCA calculations
            keys = ['product', 'name', 'location', 'database', 'functional unit', 'unit', 'method']
            data = []
            for lcia_data in self.lcaData.LCIA_calculations.values():
                data.append(dict(lcia_data.items() + self.lcaData.getActivityData(lcia_data['key']).items()))
            self.table_previous_calcs = self.helper.update_table(
                self.table_previous_calcs, data, keys)
            # Update LCA results
            self.update_LCA_results(uuid_)
            self.tab_widget_RIGHT.setCurrentIndex(self.tab_widget_RIGHT.indexOf(self.widget_LCIA_Results))

    def calculate_monte_carlo(self):
        self.calculate_lcia(monte_carlo=True)

    def load_previous_LCA_results(self, item):
        # print "DOUBLECLICK on: ", item.text()
        if item.uuid_:
            print "Loading LCA Results for:", str(item.text())
            self.update_LCA_results(item.uuid_)
        else:
            print "Error: Item does not have a UUID"

    def update_LCA_results(self, uuid_):
        lcia_data = self.lcaData.LCIA_calculations[uuid_]
        ad = self.lcaData.getActivityData(lcia_data['key'])
        # Update Labels
        self.label_LCAR_product.setText(ad['product'])
        self.label_LCAR_activity.setText("".join([ad['name'], " {", ad['location'], "}"]))
        self.label_LCAR_database.setText(ad['database'])
        self.label_LCAR_fu.setText(" ".join(["{:.3g}".format(lcia_data['functional unit']), ad['unit']]))
        self.label_LCAR_method.setText(", ".join([m for m in lcia_data['method']]))
        self.label_LCAR_score.setText("{:.3g} {:}".format(lcia_data['score'], bw2.methods[lcia_data['method']]['unit']))
        # Tables
        # Top Processes
        keys = ['inventory', 'unit', 'name', 'impact score', '%']
        data = []
        for row in lcia_data['top processes']:
            acd = self.lcaData.getActivityData(row[-1])
            data.append({
                'inventory': "{:.3g}".format(row[1]),
                'unit': acd['unit'],
                'impact score': "{:.3g}".format(row[0]),
                '%': "{:.2f}".format(100*row[0]/lcia_data['score']),
                'name': acd['name'],
            })
        self.table_top_processes = self.helper.update_table(
            self.table_top_processes, data, keys)
        # Top Emissions
        data = []
        for row in lcia_data['top emissions']:
            acd = self.lcaData.getActivityData(row[-1])
            data.append({
                'inventory': "{:.3g}".format(row[1]),
                'unit': acd['unit'],
                'impact score': "{:.3g}".format(row[0]),
                '%': "{:.2f}".format(100*row[0]/lcia_data['score']),
                'name': acd['name'],
            })
        self.table_top_emissions = self.helper.update_table(
            self.table_top_emissions, data, keys)
        # Monte Carlo
        if uuid_ in self.lcaData.LCIA_calculations_mc.keys():
            self.plot_figure_mc(self.lcaData.LCIA_calculations_mc[uuid_])
        else:
            self.figure_mc.clf()
            self.canvas_mc.draw()

    def plot_figure_mc(self, mc):
        ''' plot matplotlib Monte Carlo figure '''
        # get matplotlib figure data
        hist = np.array(mc['histogram'])
        smoothed = np.array(mc['smoothed'])
        values = hist[:, 0]
        bins = hist[:, 1]
        sm_x = smoothed[:, 0]
        sm_y = smoothed[:, 1]
        median = mc['statistics']['median']
        mean = mc['statistics']['mean']
        lconfi, upconfi =mc['statistics']['interval'][0], mc['statistics']['interval'][1]

        # plot
        self.figure_mc.clf()
        ax = self.figure_mc.add_subplot(111)
        plt.rcParams.update({'font.size': 10})
        ax.plot(values, bins)
        ax.plot(sm_x, sm_y)
        ax.vlines(lconfi, 0 , sm_y[0],
                  label='lower 95%: {:.3g}'.format(lconfi), color='red', linewidth=2.0)
        ax.vlines(upconfi, 0 , sm_y[-1],
                  label='upper 95%: {:.3g}'.format(upconfi), color='red', linewidth=2.0)
        ax.vlines(median, 0 , sm_y[self.helper.find_nearest(sm_x, median)],
                  label='median: {:.3g}'.format(median), color='magenta', linewidth=2.0)
        ax.vlines(mean, 0 , sm_y[self.helper.find_nearest(sm_x, mean)],
                  label='mean: {:.3g}'.format(mean), color='blue', linewidth=2.0)
        plt.xlabel('LCA scores ('+str(mc['iterations'])+' runs)'), plt.ylabel('probability')
        plt.legend(loc='upper right', prop={'size': 10})
        self.canvas_mc.draw()

    # ACTIVITY EDITOR (AE)

    def edit_activity(self):
        if self.lcaData.currentActivity:
            self.lcaData.set_edit_activity(self.lcaData.currentActivity)
            self.update_AE_tables()
            self.tab_widget_RIGHT.setCurrentIndex(self.tab_widget_RIGHT.indexOf(self.widget_AE))
            self.update_read_and_write_database_list()
        else:
            self.status_message.setText("Load an activity first.")

    def add_exchange_to_edited_activity(self, items):
        for item in items:
            self.lcaData.add_exchange(item.activity_or_database_key)
        self.update_AE_tables()

    def remove_exchange_from_edited_activity(self, items):
        for item in items:
            self.lcaData.remove_exchange(item.activity_or_database_key)
        self.update_AE_tables()

    def change_values_activity(self):
        item = self.table_AE_activity.currentItem()
        print "Changed value: " + str(item.text())
        header = str(self.table_AE_activity.horizontalHeaderItem(self.table_AE_activity.currentColumn()).text())
        self.lcaData.change_activity_value(str(item.text()), type=header)
        self.update_AE_tables()

    def change_exchange_values(self, item):
        self.lcaData.change_exchange_value(item.activity_or_database_key, str(item.text()), "amount")
        self.update_AE_tables()

    def save_edited_activity(self, overwrite=False):
        if overwrite:
            key = self.lcaData.editActivity_key
        else:
            key = (unicode(str(self.combo_databases.currentText())), unicode(uuid.uuid4().urn[9:]))
        if str(self.table_AE_activity.item(0, 0).text()):
            name = str(self.table_AE_activity.item(0, 0).text())  # ref product
        else:
            name = str(self.table_AE_activity.item(0, 1).text())  # activity name
        values = self.lcaData.editActivity_values
        prod_exc_data = {
            "name": name,
            "amount": float(self.table_AE_activity.item(0, 2).text()),
            "input": key,
            "type": "production",
            "unit": str(self.table_AE_activity.item(0, 3).text()),
        }
        print "\nSaving\nKey: " + str(key)
        print "Values:"
        pprint.pprint(values)
        print "Production exchange: " + str(prod_exc_data)
        self.lcaData.save_activity_to_database(key, values, prod_exc_data)
        if overwrite:
            self.status_message.setText("Replaced existing activity.")
        else:
            self.status_message.setText("Saved as new activity.")

    def replace_edited_activity(self):
        key = self.lcaData.editActivity_key
        if key[0] in browser_settings.read_only_databases:
            self.status_message.setText('Cannot save to protected database "'+str(key[0])+'". See settings file.')
        else:
            self.save_edited_activity(overwrite=True)

    def delete_activity(self):
        key = self.table_search.currentItem().activity_or_database_key
        if key[0] not in browser_settings.read_only_databases:
            mgs = "Delete this activity?"
            reply = QtGui.QMessageBox.question(self, 'Message',
                        mgs, QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
            if reply == QtGui.QMessageBox.Yes:
                self.lcaData.delete_activity(key)
                self.status_message.setText("Deleted activity: "+str(key))
            else:
                self.status_message.setText("Yeah... better safe than sorry.")
        else:
            self.status_message.setText("Not allowed to delete from: "+str(key[0]))

    def update_AE_tables(self):
        keys = ['product', 'name', 'amount', 'unit', 'location']
        ad = self.lcaData.getActivityData(values=self.lcaData.editActivity_values)
        # ad['database'] = "please choose"  # for safety reasons. You do not want to modify ecoinvent data.
        self.table_AE_activity = self.helper.update_table(
            self.table_AE_activity, [ad], keys, edit_keys=keys)
        exchanges = self.lcaData.editActivity_values['exchanges']
        self.table_AE_technosphere = self.helper.update_table(
            self.table_AE_technosphere,
            self.lcaData.get_exchanges(exchanges=exchanges, type="technosphere"),
            self.get_table_headers(type="technosphere"), edit_keys=['amount'])
        self.table_AE_biosphere = \
            self.helper.update_table(
                self.table_AE_biosphere,
                self.lcaData.get_exchanges(exchanges=exchanges, type="biosphere"),
                self.get_table_headers(type="biosphere"), edit_keys=['amount'])
        self.table_AE_activity.setMaximumHeight(
            self.table_AE_activity.horizontalHeader().height() +
            self.table_AE_activity.rowHeight(0) +
            self.table_AE_activity.autoScrollMargin()
        )

    def update_read_and_write_database_list(self):
        db_for_saving = [db['name'] for db in self.lcaData.getDatabases()
                         if db['name'] not in browser_settings.read_only_databases]
        if not db_for_saving:
            self.status_message.setText('No database found that is not read-only. '
                                         'Please add a database that can be saved to.')
        else:
            for name in db_for_saving:
                self.combo_databases.addItem(name)

    # CURRENTLY UNUSED CODE

    def add_dock(self, widget, dockName, area, tab_pos=None):
        dock = QtGui.QDockWidget(dockName)
        dock.setWidget(widget)
        dock.setFeatures(QtGui.QDockWidget.DockWidgetClosable |
                         QtGui.QDockWidget.DockWidgetMovable |
                         QtGui.QDockWidget.DockWidgetFloatable)
        self.addDockWidget(area, dock)
        self.map_dock_name.update({dock: dockName})
        self.map_name_dock.update({dockName: dock})
        self.dock_info.update()
        self.dock_info.update({
            dockName: {
                'area': area,
                'tab position': tab_pos,
            }
        })

    def position_docks_at_start(self):
        """
        Set areas and tab positions. Override with information from settings file.
        """
        # Update self.dock_info based on settings file
        for area, dock_names in browser_settings.dock_positions_at_start.items():
            for index, dock_name in enumerate(dock_names):
                self.dock_info[dock_name].update({
                    'area': area,
                    'tab position': index,
                })

        # assign all docks to areas
        for name, info in self.dock_info.items():
            self.areas.setdefault(info['area'], []).append(name)
        # print areas

        # order dock names in areas
        for area, dock_names in self.areas.items():
            # remove names from settings file from dock_names
            preset_names = browser_settings.dock_positions_at_start[area]
            for name in preset_names:
                dock_names.remove(name)
            self.areas[area] = preset_names + dock_names

    def update_dock_positions(self):
        # place docks in areas
        for name, dock in self.map_name_dock.items():
            area = self.dock_info[name]['area']
            self.addDockWidget(area, dock)
        # tabify docks
        for area, dock_names in self.areas.items():
            if len(dock_names) > 1:
                for index in range(0, len(dock_names) - 1):
                    self.tabifyDockWidget(self.map_name_dock[dock_names[index]],
                                          self.map_name_dock[dock_names[index + 1]])

def main():
    app = QtGui.QApplication(sys.argv)
    mw = MainWindow()

    # AUTO-START CUSTOMIZATION
    # mw.setUpMPEditor()
    # mw.lcaData.loadDatabase('ecoinvent 2.2')
    # mw.load_new_current_activity()

    # wnd.resize(800, 600)
    mw.showMaximized()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()