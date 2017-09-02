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
  'dijit/form/Button',
  'dijit/form/DropDownButton',
  'dijit/layout/BorderContainer',
  'dijit/layout/ContentPane',
  'dijit/layout/TabContainer',
  'codechecker/CheckerStatistics',
  'codechecker/hashHelper',
  'codechecker/ListOfBugs',
  'codechecker/ListOfRuns',
  'codechecker/util'],
function (declare, topic, domConstruct, Dialog, DropDownMenu, MenuItem,
  Button, DropDownButton, BorderContainer, ContentPane, TabContainer,
  CheckerStatistics, hashHelper, ListOfBugs, ListOfRuns, util) {

  return function () {

    //---------------------------- Global objects ----------------------------//

    CC_SERVICE = new codeCheckerDBAccess_v6.codeCheckerDBAccessClient(
      new Thrift.Protocol(new Thrift.Transport(
        "v" + CC_API_VERSION + "/CodeCheckerService")));

    CC_OBJECTS = codeCheckerDBAccess_v6;

    CC_AUTH_SERVICE =
      new codeCheckerAuthentication_v6.codeCheckerAuthenticationClient(
        new Thrift.TJSONProtocol(
          new Thrift.Transport("/v" + CC_API_VERSION + "/Authentication")));

    CC_AUTH_OBJECTS = codeCheckerAuthentication_v6;

    CC_PROD_SERVICE =
      new codeCheckerProductManagement_v6.codeCheckerProductServiceClient(
        new Thrift.Protocol(new Thrift.Transport(
          "v" + CC_API_VERSION + "/Products")));

    CC_PROD_OBJECTS = codeCheckerProductManagement_v6;

    //----------------------------- Main layout ------------------------------//

    var layout = new BorderContainer({ id : 'mainLayout' });

    var headerPane = new ContentPane({ id : 'headerPane', region : 'top' });
    layout.addChild(headerPane);

    var runsTab = new TabContainer({ region : 'center' });
    layout.addChild(runsTab);

    //--- Logo ---//

    CURRENT_PRODUCT = CC_PROD_SERVICE.getCurrentProduct();
    var currentProductName = util.atou(CURRENT_PRODUCT.displayedName_b64);
    document.title = currentProductName + ' - CodeChecker';

    var logoContainer = domConstruct.create('div', {
      id : 'logo-container'
    }, headerPane.domNode);

    var logo = domConstruct.create('span', { id : 'logo' }, logoContainer);

    var logoText = domConstruct.create('div', {
      id : 'logo-text',
      innerHTML : 'CodeChecker ' + CC_SERVICE.getPackageVersion()
    }, logoContainer);

    var title = domConstruct.create('span', {
      id : 'logo-title',
      innerHTML : currentProductName
    }, logoText);

    var user = CC_AUTH_SERVICE.getLoggedInUser();
    var loginUserSpan = null;
    if (user.length > 0) {
      loginUserSpan = domConstruct.create('span', {
        id: 'loggedin',
        innerHTML: "Logged in as " + user + "."
      });
    }

    //--- Menu button ---//

    var credits = new Dialog({
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

    var menuItems = new DropDownMenu();

    menuItems.addChild(new MenuItem({
      label : 'CodeChecker @ GitHub',
      onClick : function () {
        window.open('http://github.com/Ericsson/codechecker', '_blank');
      }
    }));

    menuItems.addChild(new MenuItem({
      label : 'Send bug report',
      onClick : function () {
        window.open('http://github.com/Ericsson/codechecker/issues/new', '_blank');
      }
    }));

    menuItems.addChild(new MenuItem({
      label : 'Credits',
      onClick : function () { credits.show(); }
    }));

    var menuButton = new DropDownButton({
      class : 'main-menu-button',
      iconClass : 'dijitIconFunction',
      dropDown : menuItems
    });

    //--- Back button to product list ---//

    var productListButton = new Button({
      class : 'main-menu-button',
      label : 'Back to product list',
      onClick : function () {
        // Use explicit URL here, as '/' could redirect back to this product
        // if there is only one product.
        window.open('/products.html', '_self');
      }
    });

    var headerMenu = domConstruct.create('div', {
        id : 'header-menu'
      });

    if (loginUserSpan != null)
        domConstruct.place(loginUserSpan, headerMenu);

    domConstruct.place(productListButton.domNode, headerMenu);

    domConstruct.place(menuButton.domNode, headerMenu);

    domConstruct.place(headerMenu, headerPane.domNode);

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

        if (urlValues.allReports) {
          topic.publish('tab/allReports')
        } else if (urlValues.checkerStatistics) {
          topic.publish('tab/checkerStatistics')
        } else if (urlValues.run) {
          topic.publish('openRun',
            findRunData(parseInt(urlValues.run)), urlValues.filters);
        } else if (urlValues.baseline || urlValues.newcheck ||
          urlValues.difftype) {
          topic.publish('openDiff', {
            baseline : findRunData(parseInt(urlValues.baseline)),
            newcheck : findRunData(parseInt(urlValues.newcheck)),
            difftype : urlValues.difftype
                     ? urlValues.difftype : CC_OBJECTS.DiffType.NEW
          });
        }

        if (urlValues.report)
          topic.publish('openFile', parseInt(urlValues.report));
      },
      onShow : function () {
        if (!this.initalized) {
          this.initalized = true;
          return;
        }

        hashHelper.clear();
      }
    });

    runsTab.addChild(listOfRuns);

    //--- Check static tab ---//

    var checkerStatisticsTab = new CheckerStatistics({
      title : 'Checker statistics',
      onShow : function () {
        var state = {
          'checkerStatistics' : true,
          'run' : this._filterPane.selectedRuns
        };

        hashHelper.setStateValues(state);
      },

      onHide : function () {
        hashHelper.setStateValue('checkerStatistics', null);
      }
    });
    runsTab.addChild(checkerStatisticsTab);

    var listOfAllReports = new ListOfBugs({
      title : 'All reports',
      allReportView : true
    });

    runsTab.addChild(listOfAllReports);

    //--- Init page ---//

    document.body.appendChild(layout.domNode);
    layout.startup();

    //------------------------------- Control --------------------------------//

    var runIdToTab = {};

    topic.subscribe('openRun', function (runData, filters) {
      if (!(runData.runId in runIdToTab)) {
        runIdToTab[runData.runId] = new ListOfBugs({
          runData : runData,
          title : runData.name,
          filters : filters,
          closable : true,
          onClose : function () {
            delete runIdToTab[runData.runId];
            return true;
          }
        });

        runsTab.addChild(runIdToTab[runData.runId]);
      }

      runsTab.selectChild(runIdToTab[runData.runId]);
    });

    topic.subscribe('openDiff', function (diff, filters) {
      var tabId = (diff.baseline ? diff.baseline.runId : 'All') + ':'
        + (diff.newcheck ? diff.newcheck.runId : 'All');

      if (!(tabId in runIdToTab)) {
        runIdToTab[tabId] = new ListOfBugs({
          baseline : diff.baseline,
          newcheck : diff.newcheck,
          difftype : diff.difftype,
          title : 'Diff of ' + (diff.baseline ? diff.baseline.name : 'All')
            + (diff.newcheck ? ' and ' + diff.newcheck.name : ''),
          closable : true,
          onClose : function () {
            delete runIdToTab[tabId];
            return true;
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

    topic.subscribe('tab/allReports', function () {
      runsTab.selectChild(listOfAllReports);
    });

    topic.subscribe('tab/checkerStatistics', function () {
      runsTab.selectChild(checkerStatisticsTab);
    });
  };
});
