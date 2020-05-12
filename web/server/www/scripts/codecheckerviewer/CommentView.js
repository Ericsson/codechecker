// -------------------------------------------------------------------------
//  Part of the CodeChecker project, under the Apache License v2.0 with
//  LLVM Exceptions. See LICENSE for license information.
//  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
// -------------------------------------------------------------------------

define([
  'dojo/_base/declare',
  'dojo/dom-construct',
  'dojo/dom-style',
  'dojo/topic',
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
function (declare, dom, style, topic, Memory, Observable, ConfirmDialog,
  Dialog, ContentPane, Button, SimpleTextarea, TextBox, ObjectStoreModel,
  HtmlTree, util) {

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
          var message = that._content.get('value');
          if (!message.trim()) {
            return;
          }

          var commentData = new CC_OBJECTS.CommentData({ message: message });
          try {
            CC_SERVICE.addComment(that.reportId, commentData);
          } catch (ex) { util.handleThriftException(ex); }
          topic.publish('showComments', that.reportId, that.sender);
        }
      });
    },

    postCreate : function () {
      this.addChild(this._content);
      this.addChild(this._commentBtn);
    }
  });

  var UserComment = declare(ContentPane, {
    postCreate : function () {
      var that = this;

      //--- Header section ---//

      var header = dom.create('div', { class : 'header'}, this.domNode);

      var avatar = util.createAvatar(this.commentData.author);
      dom.place(avatar, header);

      var vb = dom.create('div', { class : 'vb'}, header);

      dom.create('span', { class : 'author', innerHTML: this.commentData.author }, vb);

      var time = util.timeAgo(new Date(this.commentData.createdAt.replace(/ /g,'T')));
      dom.create('span', { class : 'time', innerHTML: time }, vb);

      //--- Comment operations (edit, remove) ---//
      var user = '';
      try {
        user = CC_AUTH_SERVICE.getLoggedInUser();
      } catch (ex) { util.handleThriftException(ex); }
      
      if (this.commentData.author === 'Anonymous' ||
          user === this.commentData.author
      ) {
          var operations = dom.create('div', { class : 'operations'}, header);
          dom.create('span', {
              class   : 'customIcon edit',
              onclick : function () { that.edit(); }
          }, operations);

          dom.create('span', {
              class   : 'customIcon delete',
              onclick : function () { that.remove(); }
          }, operations);
      }
      //--- Message section ---//

      this._message = dom.create('div', {
        class : 'message',
        innerHTML : this.commentData.message.replace(/(?:\r\n|\r|\n)/g, '<br>')
      }, this.domNode);

      //--- Remove comment confirmation dialog ---//

      this._removeDialog = new ConfirmDialog({
        title     : 'Remove comment',
        content   : 'Are you sure you want to delete this?',
        onExecute : function () {
          try {
            CC_SERVICE.removeComment(that.commentData.id);
          } catch (ex) { util.handleThriftException(ex); }
          topic.publish('showComments', that.reportId, that.sender);
        }
      });

      //--- Edit comment dialog ---//

      this._editDialog = new Dialog({
        title : 'Edit comment'
      });

      this._commentContent = new SimpleTextarea({
        value : this.commentData.message
      });
      this._editDialog.addChild(this._commentContent);

      this._saveButton = new Button({
        label : 'Save',
        onClick : function () {
          var newContent = that._commentContent.get('value');
          if (!newContent.trim()) {
            return;
          }

          try {
            CC_SERVICE.updateComment(that.commentData.id, newContent);
          } catch (ex) { util.handleThriftException(ex); }

          that._message.innerHTML =
            newContent.replace(/(?:\r\n|\r|\n)/g, '<br>');

          that._editDialog.hide();
        }
      });
      this._editDialog.addChild(this._saveButton);
    },

    remove : function () {
      this._removeDialog.show();
    },

    edit : function () {
      this._editDialog.show();
    }
  });

  var SystemComment = declare(ContentPane, {
    postCreate : function () {
      var wrapper = dom.create('div', { class : 'wrapper'}, this.domNode);

      dom.create('span', { class : 'system-comment-icon' }, wrapper);

      // Create comment time.
      var timeAgo = util.timeAgo(new Date(this.commentData.createdAt.replace(/ /g,'T')));
      var time = dom.create('span', { class : 'time', innerHTML: timeAgo });

      // Create comment author.
      var author = dom.create('span', {
        class : 'author',
        innerHTML: this.commentData.author
      });

      // Replace special string in comment message.
      var message = this.commentData.message;
      message = message
        .replace('%author%', author.outerHTML)
        .replace('%date%', time.outerHTML);

      var divMsg = dom.create('div', {
        class : 'message',
        innerHTML: message
      }, wrapper);

      this.addStatusIcons(divMsg);
    },

    addStatusIcons : function (domElement) {
      ['detection-status', 'review-status'].forEach(function (type) {
        ['old-' + type, 'new-' + type].forEach(function (className) {
          var domStatuses =
            domElement.getElementsByClassName(className);

          for (var i = 0; i < domStatuses.length; i++) {
            var domStatus = domStatuses[i];
            var status = domStatus.innerHTML.toLowerCase();
            domElement.insertBefore(
              dom.create('i', { class : 'customIcon ' + type + '-' + status}),
              domStatus);
          }
        });
      });
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

      topic.subscribe('showComments', function (reportId, sender) {
        if (sender !== that.sender)
          return;

        //--- Remove children ---//

        that._removeChildren(that._reply);
        that._removeChildren(that._comments);

        //--- Add reply fields and comments ---//

        that._reply.addChild(new Reply({
          class    : 'reply',
          reportId : reportId,
          sender   : sender
        }));

        var comments = [];
        try {
          comments = CC_SERVICE.getComments(reportId);
        } catch (ex) { util.handleThriftException(ex); }

        comments.forEach(function (comment) {
          if (comment.kind === CC_OBJECTS.CommentKind.SYSTEM) {
            that._comments.addChild(new SystemComment({
              class : 'system-comment',
              commentData : comment
            }));
          } else {
            that._comments.addChild(new UserComment({
              class       : 'comment',
              reportId    : reportId,
              commentData : comment,
              sender      : sender
            }));
          }
        });
      });
    }
  });
});
