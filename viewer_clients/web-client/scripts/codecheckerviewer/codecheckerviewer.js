// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  'dojo/_base/declare',
  'dojo/topic',
  'dojo/dom-construct',
  'dijit/Dialog',
  'dijit/DropDownMenu',
  'dijit/MenuItem',
  'dijit/form/DropDownButton',
  'dijit/layout/BorderContainer',
  'dijit/layout/ContentPane',
  'dijit/layout/TabContainer',
  'codechecker/hashHelper',
  'codechecker/ListOfBugs',
  'codechecker/ListOfRuns',
  'codechecker/util'],
function (declare, topic, domConstruct, Dialog, DropDownMenu, MenuItem,
  DropDownButton, BorderContainer, ContentPane, TabContainer, hashHelper,
  ListOfBugs, ListOfRuns, util) {

  return function () {

    //---------------------------- Global objects ----------------------------//

    CC_SERVICE = new codeCheckerDBAccess.codeCheckerDBAccessClient(
      new Thrift.Protocol(new Thrift.Transport("CodeCheckerService")));

    CC_OBJECTS = codeCheckerDBAccess;

    CC_SERVICE.getSuppressFile(function (filePath) {
      CC_SUPPRESS_FILE_EXISTS
        = filePath instanceof RequestFailed
        ? false
        : (filePath !== '')
    });

    //----------------------------- Main layout ------------------------------//

    var layout = new BorderContainer({ id : 'mainLayout' });

    var headerPane = new ContentPane({ id : 'headerPane', region : 'top' });
    layout.addChild(headerPane);

    var runsTab = new TabContainer({ region : 'center' });
    layout.addChild(runsTab);

    //--- Logo ---//

    var logo = domConstruct.create('div', {
      id : 'logo',
      innerHTML : 'CodeChecker'
    });

    domConstruct.place(logo, headerPane.domNode);

    //--- Menu button ---//

    var credits = new Dialog({
      title : 'Credits',
      class : 'credits',
      content :
        '<b>D&aacute;niel Krupp</b> <a href="https://github.com/dkrupp">@dkrupp</a><br>daniel.krupp@ericsson.com<br> \
         <b>Gy&ouml;rgy Orb&aacute;n</b> <a href="https://github.com/gyorb">@gyorb</a><br>gyorgy.orban@ericsson.com<br> \
         <b>Boldizs&aacute;r T&oacute;th</b> <a href="https://github.com/bobszi">@bobszi</a><br>toth.boldizsar@gmail.com<br> \
         <b>G&aacute;bor Alex Isp&aacute;novics</b> <a href="https://github.com/igalex">@igalex</a><br>gabor.alex.ispanovics@ericsson.com<br> \
         <b>Bence Babati</b> <a href="https://github.com/babati">@babati</a><br>bence.babati@ericsson.com<br> \
         <b>G&aacute;bor Horv&aacuteth</b> <a href="https://github.com/Xazax-hun">@Xazax-hun</a><br>gabor.a.horvath@ericsson.com<br> \
         <b>Szabolcs Sipos</b> <a href="https://github.com/labuwx">@labuwx</a><br>labuwx@balfug.com<br> \
         <b>Tibor Brunner</b> <a href="https://github.com/bruntib">@bruntib</a><br>tibor.brunner@ericsson.com<br>'
    });

    var menuItems = new DropDownMenu();

    menuItems.addChild(new MenuItem({
      label : 'Link to GitHub',
      onClick : function () {
        window.open('https://github.com/Ericsson/codechecker', '_blank');
      }
    }));

    menuItems.addChild(new MenuItem({
      label : 'Credits',
      onClick : function () { credits.show(); }
    }));

    var menuButton = new DropDownButton({
      class : 'mainMenuButton',
      iconClass : 'dijitIconFunction',
      dropDown : menuItems
    });

    headerPane.addChild(menuButton);

    //--- Center panel ---//

    var listOfRuns = new ListOfRuns({
      title : 'List of runs',
      onLoaded : function (runDataList) {
        function findRunData(runId) {
          return util.findInArray(runDataList, function (runData) {
            return runData.runId === runId;
          });
        }

        var urlValues = hashHelper.getValues();

        if (urlValues.run)
          topic.publish('openRun',
            findRunData(parseInt(urlValues.run)));
        else if (urlValues.baseline && urlValues.newcheck)
          topic.publish('openDiff', {
            baseline : findRunData(parseInt(urlValues.baseline)),
            newcheck : findRunData(parseInt(urlValues.newcheck))
          });

        if (urlValues.report)
          topic.publish('openFile', parseInt(urlValues.report));
      }
    });

    runsTab.addChild(listOfRuns);

    //--- Init page ---//

    document.body.appendChild(layout.domNode);
    layout.startup();

    //------------------------------- Control --------------------------------//

    var runIdToTab = {};

    topic.subscribe('openRun', function (runData) {
      if (!(runData.runId in runIdToTab)) {
        runIdToTab[runData.runId] = new ListOfBugs({
          runData : runData,
          title : runData.name,
          closable : true,
          onClose : function () {
            delete runIdToTab[runData.runId];
            return true;
          },
          onShow : function () {
            hashHelper.setRun(runData.runId);
          }
        });

        runsTab.addChild(runIdToTab[runData.runId]);
      }

      runsTab.selectChild(runIdToTab[runData.runId]);
    });

    topic.subscribe('openDiff', function (diff) {
      var tabId = diff.baseline.runId + ':' + diff.newcheck.runId;

      if (!(tabId in runIdToTab)) {
        runIdToTab[tabId] = new ListOfBugs({
          baseline : diff.baseline,
          newcheck : diff.newcheck,
          title : 'Diff of ' + diff.baseline.name + ' and ' + diff.newcheck.name,
          closable : true,
          onClose : function () {
            delete runIdToTab[tabId];
            return true;
          },
          onShow : function () {
            hashHelper.setDiff(diff.baseline.runId, diff.newcheck.runId);
          }
        });

        runsTab.addChild(runIdToTab[tabId]);
      }

      runsTab.selectChild(runIdToTab[tabId]);
    });

    var docDialog = new Dialog();

    topic.subscribe('showDocumentation', function (checkerId) {
      CC_SERVICE.getCheckerDoc(checkerId, function (documentation) {
        docDialog.set('title', 'Documentation for <b>' + checkerId + '</b>');
        docDialog.set('content', marked(documentation));
        docDialog.show();
      });
    });
  };
});
