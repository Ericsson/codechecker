// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  'dojo/_base/declare',
  'dojo/topic',
  'dijit/Dialog',
  'dijit/DropDownMenu',
  'dijit/form/DropDownButton',
  'dijit/MenuItem'],
function (declare, topic, Dialog, DropDownMenu, DropDownButton, MenuItem) {

  var HeaderMenuItems = declare(DropDownMenu, {
    postCreate : function () {
      this.inherited(arguments);

      var that = this;

      this.addChild(new MenuItem({
        label : 'CodeChecker @ GitHub',
        onClick : function () {
          window.open('http://github.com/Ericsson/codechecker', '_blank');
        }
      }));

      this.addChild(new MenuItem({
        label : 'Send bug report',
        onClick : function () {
          window.open('http://github.com/Ericsson/codechecker/issues/new',
            '_blank');
        }
      }));

      this.addChild(new MenuItem({
        label : 'Credits',
        postCreate : function () {
          this._creditsDialog = new Dialog({
            title : 'Credits',
            class : 'credits',
            content :
              '<b>D&aacute;niel Krupp</b> <a href="http://github.com/dkrupp">@dkrupp</a><br /> \
                 daniel.krupp@ericsson.com<br /> \
               <b>Gy&ouml;rgy Orb&aacute;n</b> <a href="http://github.com/gyorb">@gyorb</a><br /> \
                 gyorgy.orban@ericsson.com<br /> \
               <b>Tibor Brunner</b> <a href="http://github.com/bruntib">@bruntib</a><br /> \
                 tibor.brunner@ericsson.com<br /> \
               <b>G&aacute;bor Horv&aacute;th</b> <a href="http://github.com/Xazax-hun">@Xazax-hun</a><br /> \
                 gabor.a.horvath@ericsson.com<br /> \
               <b>Rich&aacute;rd Szalay</b> <a href="http://github.com/whisperity">@whisperity</a><br /> \
                 richard.szalay@ericsson.com<br /> \
               <b>M&aacute;rton Csord&aacute;s</b> <a href="http://github.com/csordasmarton">@csordasmarton</a><br /> \
                 marton.csordas@ericsson.com<br /> \
               <b>Boldizs&aacute;r T&oacute;th</b> <a href="http://github.com/bobszi">@bobszi</a><br /> \
                 toth.boldizsar@gmail.com<br> \
               <b>Bence Babati</b> <a href="http://github.com/babati">@babati</a><br /> \
                 bence.babati@ericsson.com<br /> \
               <b>G&aacute;bor Alex Isp&aacute;novics</b> <a href="http://github.com/igalex">@igalex</a><br /> \
                 gabor.alex.ispanovics@ericsson.com<br /> \
               <b>Szabolcs Sipos</b> <a href="http://github.com/labuwx">@labuwx</a><br /> \
                 labuwx@balfug.com<br />'
          });
        },
        onClick : function () { this._creditsDialog.show(); }
      }));

      this.addChild(new MenuItem({
        label : 'User guide',
        onClick : function () {
          topic.publish('tab/userguide');
        }
      }));
    }
  });

  return declare(DropDownButton, {
    postCreate : function () {
      this.inherited(arguments);

      this.set('dropDown', new HeaderMenuItems());
    }
  });
});
