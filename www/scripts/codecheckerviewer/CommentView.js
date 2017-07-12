// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  'dojo/_base/declare',
  'dojo/dom-construct',
  'dojo/dom-style',
  'dojo/topic',
  'dojo/date/locale',
  'dojo/store/Memory',
  'dojo/store/Observable',
  'dijit/ConfirmDialog',
  'dijit/Dialog',
  'dijit/layout/ContentPane',
  'dijit/form/Button',
  'dijit/form/SimpleTextarea',
  'dijit/form/TextBox',
  'dijit/tree/ObjectStoreModel',
  'codechecker/HtmlTree',
  'codechecker/util'],
function (declare, dom, style, topic, locale, Memory, Observable, ConfirmDialog,
  Dialog, ContentPane, Button, SimpleTextarea, TextBox, ObjectStoreModel,
  HtmlTree, util) {

  /**
   * This function creates a hexadecimal color from a string.
   */
  function strToColor(str) {
    var hash = 0;
    for (var i = 0; i < str.length; i++)
       hash = str.charCodeAt(i) + ((hash << 5) - hash);

    var c = (hash & 0x00FFFFFF).toString(16).toUpperCase();

    return '#' + '00000'.substring(0, 6 - c.length) + c;
  }

  /**
   * Creates a human friendly relative time ago on the date.
   */
  function timeAgo(date) {
    var delta = Math.round((+new Date - date) / 1000);

    var minute = 60,
        hour   = minute * 60,
        day    = hour * 24,
        week   = day * 7,
        month  = day * 30
        year   = day * 365;

    var fuzzy;

    if (delta < 30) {
      fuzzy = 'just now.';
    } else if (delta < minute) {
      fuzzy = delta + ' seconds ago.';
    } else if (delta < 2 * minute) {
      fuzzy = 'a minute ago.'
    } else if (delta < hour) {
      fuzzy = Math.floor(delta / minute) + ' minutes ago.';
    } else if (Math.floor(delta / hour) == 1) {
      fuzzy = '1 hour ago.'
    } else if (delta < day) {
      fuzzy = Math.floor(delta / hour) + ' hours ago.';
    } else if (delta < day * 2) {
      fuzzy = 'yesterday';
    } else if (delta < week) {
      fuzzy = Math.floor(delta / day) + ' days ago.';
    } else if (delta < day * 8) {
      fuzzy = '1 week ago.';
    } else if (delta < month) {
      fuzzy = Math.floor(delta / week) + ' weeks ago.';
    } else {
      fuzzy = 'on ' + locale.format(date, "yyyy-MM-dd HH:mm");
    }

    return fuzzy;
  }

  var Reply = declare(ContentPane, {
    constructor : function () {
      var that = this;

      this._content  = new SimpleTextarea({
        class       : 'reply-content',
        placeholder : 'Leave a message...',
        rows        : 4
      });

      this._commentBtn  = new Button({
        class   : 'reply-btn',
        label   : 'Comment',
        onClick : function () {
          var commentData = new CC_OBJECTS.CommentData({
            message   : that._content.get('value')
          });
          CC_SERVICE.addComment(that.bugHash, commentData);
          topic.publish('showComments', that.bugHash, that.sender);
        }
      });
    },

    postCreate : function () {
      this.addChild(this._content);
      this.addChild(this._commentBtn);
    }
  });

  var Comment = declare(ContentPane, {
    constructor : function (args) {
      dojo.safeMixin(this, args);

      var that = this;

      //--- Header section ---//

      this._header = new ContentPane();
      var header = dom.create('div', { class : 'header'}, this._header.domNode);


      var avatar = dom.create('div', { class : 'avatar'}, header);
      style.set(avatar, 'background-color', strToColor(this.author));

      var avatarLabel = this.author.charAt(0).toUpperCase();
      var avatarContent = dom.create('div', {
        class : 'avatar-content', innerHTML: avatarLabel }, avatar);


      var vb = dom.create('div', { class : 'vb'}, header);

      dom.create('span', { class : 'author', innerHTML: this.author }, vb);

      var time = timeAgo(new Date(this.time));
      dom.create('span', { class : 'time', innerHTML: time }, vb);

      //--- Comment operations (edit, remove) ---//

      var operations = dom.create('div', { class : 'operations'}, header);
      dom.create('span', {
        class   : 'customIcon edit',
        onclick : function () { that.edit(); }
      }, operations);

      dom.create('span', {
        class   : 'customIcon delete',
        onclick : function () { that.remove(); }
      }, operations);

      //--- Message section ---//

      this._message = new ContentPane({
        class   : 'message',
        content : this.message
      });

      //--- Remove comment confirmation dialog ---//

      this._removeDialog = new ConfirmDialog({
        title     : 'Remove comment',
        content   : 'Are you sure you want to delete this?',
        onExecute : function () {
          CC_SERVICE.removeComment(that.cId);
          topic.publish('showComments', that.bugHash, that.sender);
        }
      });

      //--- Edit comment dialog ---//

      this._editDialog = new Dialog({
        title : 'Edit comment'
      });

      this._commentContent = new SimpleTextarea({
        value : that.message
      });

      this._saveButton = new Button({
        label : 'Save',
        onClick : function () {
          var newContent = that._commentContent.get('value');

          CC_SERVICE.updateComment(that.cId, newContent);

          that._message.set('content', newContent);
          that._editDialog.hide();
        }
      });
    },

    postCreate : function () {
      this.addChild(this._header);
      this.addChild(this._message);

      this._editDialog.addChild(this._commentContent);
      this._editDialog.addChild(this._saveButton);
    },

    remove : function () {
      this._removeDialog.show();
    },

    edit : function () {
      this._editDialog.show();
    }
  });

  return declare(ContentPane, {
    constructor : function () {
      this._reply = new ContentPane();
      this._comments = new ContentPane();

      this._subscribeTopics();
    },

    postCreate : function () {
      this.addChild(this._reply);
      this.addChild(this._comments)
    },

    /**
     * Helper function to remove all children of the widget.
     */
    _removeChildren : function (widget) {
      widget.getChildren().forEach(function (child) {
            widget.removeChild(child);
      }, this);
    },

    /**
     * Subscribe on topics.
     */
    _subscribeTopics : function () {
      var that = this;

      topic.subscribe('showComments', function (bugHash, sender) {
        if (sender !== that.sender)
          return;

        //--- Remove children ---//

        that._removeChildren(that._reply);
        that._removeChildren(that._comments);

        //--- Add reply fields and comments ---//

        that._reply.addChild(new Reply({
          class   : 'reply',
          bugHash : bugHash,
          sender  : sender
        }));

        var comments = CC_SERVICE.getComments(bugHash);
        comments.forEach(function (comment) {
          that._comments.addChild(new Comment({
            class   : 'comment',
            bugHash : bugHash,
            cId     : comment.id,
            author  : comment.author,
            time    : comment.createdAt,
            message : comment.message,
            sender  : sender
          }));
        });
      });
    }
  });
});