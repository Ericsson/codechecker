// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  'dojo/_base/declare',
  'dojo/cookie',
  'dojo/topic',
  'dojox/image/Lightbox',
  'dijit/Dialog',
  'dijit/form/Button',
  'dijit/layout/BorderContainer',
  'dijit/layout/ContentPane',
  'dijit/layout/TabContainer',
  'codechecker/CheckerStatistics',
  'codechecker/hashHelper',
  'codechecker/HeaderPane',
  'codechecker/ListOfBugs',
  'codechecker/ListOfRuns',
  'codechecker/util'],
function (declare, cookie, topic, Lightbox, Dialog, Button, BorderContainer,
  ContentPane, TabContainer, CheckerStatistics, hashHelper, HeaderPane,
  ListOfBugs, ListOfRuns, util) {

  function initByUrl() {
    var state = hashHelper.getValues();

    for (var key in state)
      if (key.indexOf('userguide-') !== -1) {
        topic.publish('tab/userguide');
        return;
      }

    switch (state.tab) {
      case undefined:
        if (state.run || state.newcheck || state.difftype ||
          state.reportHash || state.report)
          topic.publish('tab/allReports');
        else
          topic.publish('tab/listOfRuns');
        return;
      case 'statistics':
        topic.publish('tab/checkerStatistics');
        return;
      case 'userguide':
        topic.publish('tab/userguide');
        return;
      case 'allReports':
        topic.publish('tab/allReports');
        return;
      case 'changelog':
        topic.publish('tab/changelog');
        return;
    }

    topic.publish('openRun', {
      baseline : state.run,
      newcheck : state.newcheck,
      tabId    : state.tab,
      difftype : state.difftype ? state.difftype : CC_OBJECTS.DiffType.NEW
    });
  }

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

    CC_CONF_SERVICE =
      new codeCheckerConfiguration_v6.configurationServiceClient(
        new Thrift.Protocol(
          new Thrift.Transport("v" + CC_API_VERSION + "/Configuration")));

    CC_CONF_OBJECTS = codeCheckerConfiguration_v6;

    //----------------------------- Main layout ------------------------------//

    var layout = new BorderContainer({ id : 'mainLayout' });

    var runsTab = new TabContainer({ region : 'center' });
    layout.addChild(runsTab);

    CURRENT_PRODUCT = new CC_PROD_OBJECTS.Product();
    try {
      CURRENT_PRODUCT = CC_PROD_SERVICE.getCurrentProduct();
    } catch (ex) { util.handleThriftException(ex); }

    var currentProductName = util.atou(CURRENT_PRODUCT.displayedName_b64);
    document.title = currentProductName + ' - CodeChecker';

    IS_ADMIN_OF_ANY_PRODUCT = false;
    try {
      IS_ADMIN_OF_ANY_PRODUCT = CC_PROD_SERVICE.isAdministratorOfAnyProduct();
    } catch (ex) { util.handleThriftException(ex); }

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

    var headerPane = new HeaderPane({
      id : 'headerPane',
      title : currentProductName,
      region : 'top',
      menuItems : [ productListButton.domNode ],
      mainTab : runsTab
    });
    layout.addChild(headerPane);

    //--- Center panel ---//

    var listOfRuns = new ListOfRuns({
      title : 'Runs',
      iconClass : 'customIcon run-name',
      onLoaded : function () {
        initByUrl();
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

    var state = hashHelper.getState();

    var listOfAllReports = new ListOfBugs({
      title : 'All reports',
      iconClass : 'customIcon all-reports',
      allReportView : true,
      tab : 'allReports',
      openedByUserEvent : state['tab'] !== 'allReports'
    });

    //--- Check static tab ---//

    var checkerStatisticsTab = new CheckerStatistics({
      class : 'checker-statistics',
      title : 'Checker statistics',
      iconClass : 'customIcon statistics',
      listOfAllReports : listOfAllReports,
      tab : 'statistics',
      openedByUserEvent : state.tab !== 'statistics'
    });
    runsTab.addChild(checkerStatisticsTab);
    runsTab.addChild(listOfAllReports);

    var changelogPage = null;

    //--- Init page ---//

    document.body.appendChild(layout.domNode);
    layout.startup();

    var packageVersion = '';
    try {
      packageVersion = CC_PROD_SERVICE.getPackageVersion();
    } catch (ex) { util.handleThriftException(ex); }

    //------------------------------- Control --------------------------------//

    var runIdToTab = {};

    topic.subscribe('openRun', function (param) {
      var tabId = param.tabId;

      var baseline = param.baseline;
      if (baseline && !(baseline instanceof Array))
        baseline = [baseline];

      var newcheck = param.newcheck;
      if (newcheck && !(newcheck instanceof Array))
        newcheck = [newcheck];

      if (!(tabId in runIdToTab)) {
        var runs = tabId.split('_diff_');
        var title = runs.length == 2
          ? 'Diff of ' + runs[0] + ' and ' + runs[1]
          : runs[0];

        runIdToTab[tabId] = new ListOfBugs({
          baseline : baseline,
          newcheck : newcheck,
          title : title,
          iconClass : 'customIcon reports',
          closable : true,
          tab : tabId,
          openedByUserEvent : param.openedByUserEvent,
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
      var markedOptions = {
            highlight: function(code) {
              return hljs.highlightAuto(code).value;
            },
          };

      try {
        CC_SERVICE.getCheckerDoc(checkerId, function (documentation) {
          docDialog.set('title', 'Documentation for <b>' + checkerId + '</b>');
          docDialog.set('content', marked(documentation, markedOptions));
          docDialog.show();
        });
      } catch (ex) { util.handleThriftException(ex); }
    });

    topic.subscribe('showReviewComment', function (reviewData) {
      if (reviewData.author) {
        var content = util.reviewStatusTooltipContent(reviewData);
        docDialog.set('title', 'Review status');
        docDialog.set('content', content);
        docDialog.show();
      }
    });

    topic.subscribe('tab/allReports', function () {
      runsTab.selectChild(listOfAllReports);
    });

    topic.subscribe('tab/checkerStatistics', function () {
      runsTab.selectChild(checkerStatisticsTab);
    });

    topic.subscribe('tab/listOfRuns', function () {
      runsTab.selectChild(listOfRuns);
    });

    //--- Handle main tabs ---//

    topic.subscribe('/dojo/hashchange', function (url) {
      initByUrl();
    });

    if (!cookie('changelog') || cookie('changelog') > packageVersion)
      topic.publish('tab/changelog', { preventSelect : true });
  };
});
