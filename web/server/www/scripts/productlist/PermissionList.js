// -------------------------------------------------------------------------
//  Part of the CodeChecker project, under the Apache License v2.0 with
//  LLVM Exceptions. See LICENSE for license information.
//  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
// -------------------------------------------------------------------------

define([
  'dojo/_base/declare',
  'dojo/dom-attr',
  'dojo/dom-class',
  'dojo/dom-construct',
  'dojo/data/ItemFileWriteStore',
  'dojo/store/Memory',
  'dojo/store/Observable',
  'dijit/Dialog',
  'dijit/form/Button',
  'dijit/form/Select',
  'dijit/form/TextBox',
  'dojox/form/CheckedMultiSelect',
  'dijit/layout/ContentPane',
  'codechecker/MessagePane',
  'codechecker/util'],
function (declare, domAttr, domClass, domConstruct, ItemFileWriteStore,
  Memory, Observable, Dialog, Button, Select, TextBox,
  CheckedMultiSelect, ContentPane, MessagePane, util) {

  return declare(ContentPane, {
    constructor : function () {
      var that = this;

      this._permissionStore = new Observable(new Memory({}));
      this._userStore = new ItemFileWriteStore({
        data : { identifier : 'value', items : [] }
      });
      this._groupStore = new ItemFileWriteStore({
        data : { identifier : 'value', items : [] }
      });

      this._selPermission = new Select({
        class     : 'form-input permission-options',
        style     : 'width: 350px',
        store     : this._permissionStore,
        labelAttr : 'label',
        onChange  : function () {
          var item = this.store.get(this.get('value'));
          that._updateSelectedUsers(item.value);
        }
      });

      /**
       * Manage the user's action when they select or unselect a permission
       * record on the interface.
       */
      function __lstChange(element, isGroup) {
        if (element.get('inhibitNextChangeEmit')) {
          // Inhibition mean we have to later act like this change never
          // happened, i.e. the permission list didn't change now.
          element.set('prevValue', element.get('value'));
          element.set('inhibitNextChangeEmit', false);
          return;
        }

        function diff(a, b) {
          return a.filter(function (x) {
            return b.indexOf(x) === -1;
          });
        }

        var permission = that._permissionStore.get(
          that._selPermission.get('value')).value;
        var prevValue = element.get('prevValue');
        var current = element.get('value');
        var added = diff(current, prevValue);
        var removed = diff(prevValue, current);

        var diffRecord = that.get('rightsDiff')[permission];
        diffRecord = isGroup ? diffRecord.groups : diffRecord.users;

        added.forEach(function (name) {
          // Each added user must be present in the "add" list,
          // and must NOT be present in the "remove" list.
          var removeIdx = diffRecord.remove.indexOf(name);

          if (removeIdx > -1)
            diffRecord.remove.splice(removeIdx, 1);

          // A user must NOT be present in the "add" list if they had the
          // permission initially.
          if (!that._hadPermissionInitially(permission, name, isGroup))
            diffRecord.add.push(name);
        });

        removed.forEach(function (name) {
          // Each removed user must be present in the "remove" list,
          // and must NOT be present in the "add" list.
          var addIdx = diffRecord.add.indexOf(name);

          if (addIdx > -1)
            diffRecord.add.splice(addIdx, 1);

          // A user must NOT be present in the "remove" list if they
          // did not have the permission initially.
          if (that._hadPermissionInitially(permission, name, isGroup))
            diffRecord.remove.push(name);
        });

        // Save the previous value.
        element.set('prevValue', current);
      }

      function __lstReset() {
        // After a reset, we don't allow for onChange() to fire.
        this.set('inhibitNextChangeEmit', true);
        this.set('prevValue', []);
        this.set('value', []);
        this._updateSelection();
      }

      function __lstAddUser(textBox, multiselect, store, nameList) {
        var name = textBox.get('value');
        if (name) {
          name = name.trim();
        }

        if (name.length > 0 && name !== "*" &&
            nameList.indexOf(name) === -1) {
          nameList.push(name);
          store.newItem({ value : name});

          // Mark the newly added authentication name ticked for the
          // current permission.
          var selected = multiselect.get('value');
          selected.push(name);
          // This triggers the rest of the operations.
          multiselect.set('value', selected);
        }

        textBox.set('value', "");
      }

      this._lstNames = new CheckedMultiSelect({
        class     : 'form-input permission-list names',
        multiple  : true,
        store     : this._userStore,
        labelAttr : 'value',
        onChange  : function () {
          __lstChange(this, false);
        },
        reset     : __lstReset
      });

      this._txtNewUser = new TextBox({
        class       : 'form-input under-multiselect',
        placeholder : "Username"
      });

      this._btnAddUser = new Button({
        class   : 'add-btn under-multiselect',
        label   : "Add",
        onClick : function () {
          __lstAddUser(that._txtNewUser, that._lstNames, that._userStore,
            that.get('nameList').users);
        }
      });

      this._lstGroups = new CheckedMultiSelect({
        class     : 'form-input permission-list groups',
        multiple  : true,
        store     : this._groupStore,
        labelAttr : 'value',
        onChange  : function () {
          __lstChange(this, true);
        },
        reset     : __lstReset
      });

      this._txtNewGroup = new TextBox({
        class       : 'form-input under-multiselect',
        placeholder : "Group name"
      });

      this._btnAddGroup = new Button({
        class   : 'add-btn under-multiselect',
        label   : "Add",
        onClick : function() {
          __lstAddUser(that._txtNewGroup, that._lstGroups, that._groupStore,
            that.get('nameList').groups);
        }
      });
    },

    /**
     * Populate the permission list on the dialog with permissions of the given
     * scope. extra_params is the scope-specific argument list, please refer
     * to the API documentation about it.
     */
    populatePermissions : function (scope, extraParams) {
      var that = this;

      this.set('scope', scope);
      this.set('extraParams', extraParams);

      // The scope-specific extra parameters are transmitted over the wire as
      // a JSON-encoded string inside the Thrift object.
      this.set('extraParamsJSON', util.createPermissionParams(extraParams));

      this._permissionStore.query().forEach(function (permItem) {
        that._permissionStore.remove(permItem.id);
      });
      this._userStore.fetch({
        onComplete : function (names) {
          names.forEach(function (name) {
            that._userStore.deleteItem(name);
          });
          that._userStore.save();
        }
      });
      this._groupStore.fetch({
        onComplete : function (names) {
          names.forEach(function (name) {
            that._groupStore.deleteItem(name);
          });
          that._groupStore.save();
        }
      });

      this._selPermission.reset();
      this._lstNames.reset();
      this._lstGroups.reset();

      var optionsToAdd = [];

      // This dict stores the list of users and groups that were
      // given a particular permission at the time of executing this function.
      var rightsMap = {};

      // This dict stores all the names and groups that are present on the
      // GUI.
      var nameList = {
        users  : [],
        groups : []
      };

      // This dict stores the difference (permission changes)
      // that will need to be applied when the changes are saved.
      var rightsDiff = {};

      var filter = new CC_AUTH_OBJECTS.PermissionFilter({
        canManage : true
      });
      var permissions = [];
      try {
        permissions = CC_AUTH_SERVICE.getPermissionsForUser(
          scope, this.get('extraParamsJSON'), filter);
      } catch (ex) { util.handleThriftException(ex); }

      permissions.forEach(function(enumValue) {
        optionsToAdd.push({
          label : util.enumValueToKey(Permission, enumValue),
          value : enumValue
        });

        var authedUsersAndGroups = new CC_AUTH_OBJECTS.AuthorisationList();
        try {
          authedUsersAndGroups = CC_AUTH_SERVICE.getAuthorisedNames(
            enumValue, that.get('extraParamsJSON'));
        } catch (ex) { util.handleThriftException(ex); }

        rightsMap[enumValue] = {
          users  : authedUsersAndGroups.users,
          groups : authedUsersAndGroups.groups
        };

        nameList.users = nameList.users.concat(authedUsersAndGroups.users);
        nameList.groups = nameList.groups.concat(authedUsersAndGroups.groups);

        rightsDiff[enumValue] = {
          users  : {
            add    : [],
            remove : []
          },
          groups : {
            add    : [],
            remove : []
          }
        }
      });

      optionsToAdd.sort(function (a, b) {
        return a.label < b.label
          ? -1 : a.label === b.label
          ? 0 : 1;
      });

      optionsToAdd.forEach(function (permissionOption) {
        that._permissionStore.put(permissionOption);
      });

      this.set('rightsMap', rightsMap);
      this.set('rightsDiff', rightsDiff);

      // Sort and unique the name list.
      nameList.users = util.arrayUnique(nameList.users.sort());
      nameList.groups = util.arrayUnique(nameList.groups.sort());

      // Transform the name lists into options for the GUI element.
      nameList.users.forEach(function(name) {
        that._userStore.newItem({value : name});
      });
      nameList.groups.forEach(function(name) {
        that._groupStore.newItem({value : name});
      });

      this.set('nameList', nameList);

      // The GUI automatically selects the first element of the permission
      // list, so we need to tick the users who have the "first" permission.
      if (optionsToAdd.length > 0)
        this._updateSelectedUsers(optionsToAdd[0].value);
    },

    /**
     * Returns whether or not the given (user or group) name was having
     * the permission when the form was populated.
     */
    _hadPermissionInitially : function (permValue, name, isGroup) {
      var mapRecord = this.get('rightsMap')[permValue];
      mapRecord = isGroup ? mapRecord.groups : mapRecord.users;
      return mapRecord.indexOf(name) !== -1;
    },

    /**
     * Returns whether the given (user or group) name should be marked as
     * having the given permission.
     */
    _hasPermission : function (permValue, name, isGroup) {
      var diffRecord = this.get('rightsDiff')[permValue];
      diffRecord = isGroup ? diffRecord.groups : diffRecord.users;

      if (this._hadPermissionInitially(permValue, name, isGroup)) {
        // If the user had the right, it could be that we removed it meanwhile.
        return diffRecord.remove.indexOf(name) === -1;
      } else {
        // If didn't, it could be that we added it since.
        return diffRecord.add.indexOf(name) !== -1;
      }
    },

    _updateSelectedUsers : function(newPermissionSelected) {
      var that = this;
      function __calculateUpdate(store, isGroup) {
        var newValue = [];

        store.fetch({
          onComplete : function (options) {
            options.forEach(function (option) {
              var markSelected = that._hasPermission(newPermissionSelected,
                option.value[0], isGroup);

              if (markSelected)
                newValue.push(option.value[0]);
            });
          }
        });

        return newValue;
      }

      this._lstNames.reset();
      var newNames = __calculateUpdate(this._userStore, false);
      // Setting value makes the onChange() event fire. To prevent the
      // changes here suddenly marking a lot of permissions changed as if the
      // user issued these actions, we set the inhibitor.
      this._lstNames.set('inhibitNextChangeEmit', newNames.length > 0);
      this._lstNames.set('value', newNames);

      this._lstGroups.reset();
      var newGroups = __calculateUpdate(this._groupStore, true);
      this._lstGroups.set('inhibitNextChangeEmit', newGroups.length > 0);
      this._lstGroups.set('value', newGroups);
    },

    /**
     * Retrieve a list of the permission changes selected by the user
     * in the form of small objects that contain the data needed to execute
     * API calls.
     */
    getPermissionDifference : function () {
      var ret = [];

      function createRecords(perm, action, isGroup, nameList) {
        nameList.forEach(function (name) {
          ret.push({
            permission : perm,
            action     : action,
            name       : name,
            isGroup    : isGroup
          });
        });
      }

      var rightsDiff = this.get('rightsDiff');
      for (var enumValue in rightsDiff) {
        var permission = parseInt(enumValue);
        var diffRecord = rightsDiff[permission];
        createRecords(permission, 'ADD', false, diffRecord.users.add);
        createRecords(permission, 'ADD', true, diffRecord.groups.add);
        createRecords(permission, 'REMOVE', false, diffRecord.users.remove);
        createRecords(permission, 'REMOVE', true, diffRecord.groups.remove);
      }

      return ret;
    },

    postCreate : function () {
      this.inherited(arguments);

      //--- Set up the form ---//

      var permSelectCont = domConstruct.create('div', {
        class : 'formElement'
      }, this.containerNode);
      var permLabel = domConstruct.create('label', {
        class     : 'formLabel bold',
        innerHTML : "Permission: "
      });
      domConstruct.place(permLabel, permSelectCont);
      domConstruct.place(this._selPermission.domNode, permSelectCont);

      var permBlock = domConstruct.create('div', {
        class : 'formElement'
      }, this.containerNode);

      var permContainer = domConstruct.create('div', {
        class : 'formElement'
      }, permBlock);

      var userContainer = domConstruct.create('div', {
        class : 'halflistContainer users'
      }, permBlock);
      domConstruct.place(this._lstNames.domNode, userContainer);
      domConstruct.place(this._txtNewUser.domNode, userContainer);
      domConstruct.place(this._btnAddUser.domNode, userContainer);

      var groupContainer = domConstruct.create('div', {
        class : 'halflistContainer groups'
      }, permBlock);
      domConstruct.place(this._lstGroups.domNode, groupContainer);
      domConstruct.place(this._txtNewGroup.domNode, groupContainer);
      domConstruct.place(this._btnAddGroup.domNode, groupContainer);

      domConstruct.place(userContainer, permContainer);
      domConstruct.place(groupContainer, permContainer);
    }
  });
});
