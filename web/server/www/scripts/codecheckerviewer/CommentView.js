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
          var commentData = new CC_OBJECTS.CommentData({
            message   : that._content.get('value')
          });
          CC_SERVICE.addComment(that.reportId, commentData);
          topic.publish('showComments', that.reportId, that.sender);
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

      var avatar = util.createAvatar(this.author);
      dom.place(avatar, header);

      var vb = dom.create('div', { class : 'vb'}, header);

      dom.create('span', { class : 'author', innerHTML: this.author }, vb);

      var time = util.timeAgo(new Date(this.time.replace(/ /g,'T')));
      dom.create('span', { class : 'time', innerHTML: time }, vb);

      //--- Comment operations (edit, remove) ---//
      var user = CC_AUTH_SERVICE.getLoggedInUser();
      
      if (this.author == 'Anonymous' || user == this.author) { 
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
          topic.publish('showComments', that.reportId, that.sender);
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

        var comments = CC_SERVICE.getComments(reportId);
        comments.forEach(function (comment) {
          that._comments.addChild(new Comment({
            class    : 'comment',
            reportId : reportId,
            cId      : comment.id,
            author   : comment.author,
            time     : comment.createdAt,
            message  : comment.message,
            sender   : sender
          }));
        });
      });
    }
  });
});
