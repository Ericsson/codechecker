// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  'dojo/_base/declare',
  'dojo/dom-class',
  'dojo/dom-construct',
  'dojo/keys',
  'dojox/widget/Standby',
  'dijit/form/TextBox',
  'dijit/popup',
  'dijit/TooltipDialog',
  'dijit/layout/ContentPane'],
function (declare, domClass, dom, keys, Standby, TextBox, popup, TooltipDialog,
  ContentPane) {

  return declare(ContentPane, {
    // Default limit of the filter queries.
    defaultQueryFilterSize : 10,

    constructor : function () {
      // Cache of the tooltip items which will be rendered.
      this.cachedIems = null;

      // DOM element of the tooltip items.
      this.itemsDom = {};

      // Stores filter changes between tooltip show and tooltip hide events.
      // This way the user can enable and disable multiple items before sending
      // notification to the other filter elements.
      this.itemChanged = {};
    },

    postCreate : function () {
      if (!this.search) this.search = {};

      var that = this;
      if (this.search.enable) {
        this._searchBox = new TextBox({
          placeholder : this.search.placeHolder,
          class       : 'select-menu-filter',
          onKeyUp     : function (e) {
            var filter = this.get('value');

            if (e.keyCode === keys.ENTER) {
              that.toggle(filter);
              return;
            }

            clearTimeout(this.timer);
            this.timer = setTimeout(function () {
              // Clear the cache if the filter uses server side search.
              if (that.search.serverSide)
                that.cachedIems = null;

              that.getItems({
                filter : filter,
                limit : that.defaultQueryFilterSize
              });
            }, 300);
          }
        });
        this.addChild(this._searchBox);
      }

      this._selectMenuList = dom.create('div', {
        class : 'select-menu-list ' + this.class
      }, this.domNode);

      this._dialog = new TooltipDialog({
        content : this.domNode,
        onBlur : function () {
          popup.close(this);

          // If there is some changes in the actual filter (some filter items
          // are added or removed), notify the other filters.
          if (Object.keys(that.itemChanged).length) {
            that.reportFilter.notifyOthers();
            that.itemChanged = {};
          }
        }
      });

      this._standBy = new Standby({
        target : this.domNode,
        color : '#ffffff'
      });
      this.addChild(this._standBy);
    },

    // This function resets the current state of the tooltip.
    // Note: on every filter change this function should be called.
    reset : function (items) {
      this.cachedIems = items;
      this.resetDomItems();
    },

    // This function resets variable which stores DOM element.
    resetDomItems : function () {
      this.itemsDom = {};
      dom.empty(this._selectMenuList);
    },

    // Shows the tooltip by rendering the tooltip items.
    show : function () {
      this._standBy.show();

      this.getItems({ limit : this.defaultQueryFilterSize });
      this.openTooltip();
    },

    openTooltip : function () {
      popup.open({
        popup : this._dialog,
        around : this.around
      });
      this._dialog.focus();
    },

    // Select a filter tooltip item. If the tooltip item is already selected
    // than do nothing with it.
    select : function (value) {
      if (this.itemsDom[value])
        domClass.add(this.itemsDom[value], 'selected');
    },

    // Deselect a filter tooltip item. If the tooltip item is not selected than
    // do nothing with it.
    deselect : function (value) {
      if (this.itemsDom[value])
        domClass.remove(this.itemsDom[value], 'selected');
    },

    // Toggle a filter item.
    toggle : function (value, item) {
      if (this.itemsDom[value])
        domClass.toggle(this.itemsDom[value], 'selected');

      // Select or deselect the filter item on the filter view.
      if (this.reportFilter.isSelected(value))
        this.reportFilter.deselect(value);
      else
        this.reportFilter.select(value, item);

      // Store the changes to identify if some new actions (add/remove filter
      // items) are made during the tooltip show and hide events. If the item
      // is already in the map, we can remove it because the item does not
      // changed since the tooltip show.
      if (this.itemChanged[value])
        delete this.itemChanged[value];
      else
        this.itemChanged[value] = true;
    },

    // Get filter tooltip items. If the filter uses server side search or no
    // filter items are cached we get the items from the filter itself.
    // Othwerwise we use the cache.
    getItems : function (opt) {
      var that = this;
      if (!this.cachedIems) {
        if (opt.filter) {
          opt.query = [ opt.filter + (this.search.regex ? '*' : '') ];
        }

        this.reportFilter.getItems(opt).then(function (items) {
          that.cachedIems = items;

          if (opt.filter && that.search.serverSide && that.search.regex) {
            that.cachedIems.unshift({
              value : opt.filter,
              isRegexSearchItem : true
            });
          }

          that.render(that.cachedIems);
        });
      } else {
        var filteredItems = this.cachedIems;
        if (opt.filter)
          filteredItems = filteredItems.filter(function (item) {
            return item.value.toString().indexOf(opt.filter) !== -1;
          });
        this.render(filteredItems);
      }
    },

    // Resets DOM items of the tooltip and render filter items.
    render : function (items) {
      this.resetDomItems();

      var that = this;

      if (!items.length) {
        dom.create('div', {
          innerHTML : this.noAvailableTooltipItemMsg
        }, this._selectMenuList);
      } else {
        items.forEach(function (item) {
          var label = (item.isRegexSearchItem ? 'Filter by RegEx: ' : '');
          label += that.reportFilter.labelFormatter
            ? that.reportFilter.labelFormatter(item.value)
            : item.value;

          var iconClass = that.reportFilter.getIconClass(item.value, item);
          var iconStyle = that.reportFilter.getIconStyle
            ? that.reportFilter.getIconStyle(item.value)
            : null;

          var content = '<span class="customIcon selected"></span>'
            + (iconClass
              ? '<span class="' + iconClass + '" style="' +
                (iconStyle ? iconStyle : '') + '"></span>'
              : '')
            + '<span class="label">' + label + '</span>';

          if (item.count !== undefined)
            content += '<span class="count">' + item.count + '</span>';

          var classes = ['select-menu-item'];
          if (that.reportFilter.isSelected(item.value)) classes.push('selected');
          if (item.isRegexSearchItem) classes.push('regex-item');

          that.itemsDom[item.value] = dom.create('div', {
            class     : classes.join(' '),
            innerHTML : content,
            title : label,
            onclick : function () {
              that.toggle(item.value, item);
            }
          }, that._selectMenuList);
        });
      }

      this._standBy.hide();

      // Some cases the tooltip overflows the window at the bottom. By
      // opening the dialog again resolves the problem.
      this.openTooltip();
    }
  });
});
