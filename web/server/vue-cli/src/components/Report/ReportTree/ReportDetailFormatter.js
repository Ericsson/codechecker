import { ExtendedReportDataType } from "@cc/report-server-types";

import ReportTreeKind from "./ReportTreeKind";
import ReportStepIconType from "./ReportStepIconType";

const highlightColours = [
  "#ffffff",
  "#e9dddd",
  "#dde0eb",
  "#e5e8e5",
  "#cbc2b6",
  "#b8ccea",
  "#c1c9cd",
  "#a7a28f"
];

function getHighlightData(stack, step) {
  let msg = step.msg;

  // The background must be saved BEFORE stack transition.
  // Calling is in the caller, return is in the called func, not "outside"
  const highlight = {
    bgColor: stack.bgColor,
    icon: ReportStepIconType.DEFAULT
  };

  function extractFuncName(prefix) {
    if (msg.startsWith(prefix)) {
      msg = msg.replace(prefix, "").replace(/'/g, "");
      return true;
    }
  }

  if (extractFuncName("Calling ")) {
    stack.funcStack.push(msg);
    stack.bgColor = highlightColours[
      stack.funcStack.length % highlightColours.length];

    highlight.icon = ReportStepIconType.CALLING;
  } else if (msg.startsWith("Entered call from ")) {
    highlight.icon = ReportStepIconType.ENTERED_CALL;
  } else if (extractFuncName("Returning from ")) {
    if (msg === stack.funcStack[stack.funcStack.length - 1]) {
      stack.funcStack.pop();
      stack.bgColor = highlightColours[
        stack.funcStack.length % highlightColours.length];

      highlight.icon = ReportStepIconType.RETURNING;
    } else {
      console.warn("StackError: Returned from " + msg
        + " while the last function " + "was "
        + stack.funcStack[stack.funcStack.length - 1]);
    }
  } else if (msg === "Returned allocated memory") {
    stack.funcStack.pop();
    stack.bgColor = highlightColours[
      stack.funcStack.length % highlightColours];
    highlight.icon = ReportStepIconType.RETURNING;
  } else if (msg.startsWith("Assuming the condition")) {
    highlight.icon = ReportStepIconType.ASSUMING_CONDITION;
  } else if (msg.startsWith("Assuming")) {
    highlight.icon = ReportStepIconType.ASSUMING;
  } else if (msg == "Entering loop body") {
    highlight.icon = ReportStepIconType.ENTERING_LOOP_BODY;
  } else if (msg.startsWith("Loop body executed")) {
    highlight.icon = ReportStepIconType.LOOP_BODY_EXECUTED;
  } else if (msg == "Looping back to the head of the loop") {
    highlight.icon = ReportStepIconType.LOOP_BACK;
  }

  return highlight;
}

function formatExtendedData(report, extendedData) {
  const items = [];

  // Add macro expansions.
  const macros = extendedData.filter(data => {
    return data.type === ExtendedReportDataType.MACRO;
  });

  if (macros.length) {
    const children = formatExtendedReportDataChildren(report, macros,
      ReportTreeKind.MACRO_EXPANSION_ITEM);

    items.push({
      id: ReportTreeKind.getId(ReportTreeKind.MACRO_EXPANSION, report),
      name: "Macro expansions",
      kind: ReportTreeKind.MACRO_EXPANSION,
      children: children
    });
  }

  // Add notes.
  const notes = extendedData.filter(data => {
    return data.type === ExtendedReportDataType.NOTE;
  });

  if (notes.length) {
    const children = formatExtendedReportDataChildren(report, notes,
      ReportTreeKind.NOTE_ITEM);

    items.push({
      id: ReportTreeKind.getId(ReportTreeKind.NOTE, report),
      name: "Notes",
      kind: ReportTreeKind.NOTE,
      children: children
    });
  }

  return items;
}

function formatExtendedReportDataChildren(report, extendedData, kind) {
  return extendedData.sort((a, b) => {
    return a.startLine - b.startLine;
  }).map((data, index) => {
    return {
      id: ReportTreeKind.getId(kind, report, index),
      name: data.message,
      kind: kind,
      data: data,
      report: report
    };
  });
}

function getReportStepIcon(step, index, isResult) {
  var type = isResult
    ? "error" : step.msg.indexOf(" (fixit)") > -1
      ? "fixit" : "info";

  return {
    index: index + 1,
    type: type
  };
}

function formatReportEvents(report, events) {
  const items = [];

  const highlightStack = {
    funcStack: [],
    bgColor: highlightColours[0]
  };

  // Check if there are multiple files (XTU?) affected by this bug.
  // If so, we show the file names properly.
  const firstFilePath = events.length ? events[0].filePath : null;
  const showFileName =
    events.some(step => step.filePath !== firstFilePath);

  // Indent path events on function calls.
  let indentation = 0;

  events.forEach(function (step, index) {
    const isResult = index === events.length - 1;

    let fileName = null;
    let shortFileName = null;
    if (showFileName) {
      fileName = step.filePath.replace(/^.*(\\|\/|:)/, "");

      shortFileName = fileName;
      if (shortFileName.length > 12) {
        const extensionParts = shortFileName.split(".");
        const fnWithoutExt =
          extensionParts.slice(0, extensionParts.length).join(".");
        const extension = (extensionParts.length > 1
          ? "." + extensionParts[extensionParts.length - 1]
          : "");
        shortFileName = fnWithoutExt.substr(0, 8) + "..." + extension;
      }
    }

    const highlightData = getHighlightData(highlightStack, step);
    const reportStepIcon = getReportStepIcon(step, index, isResult);

    if (highlightData.icon === ReportStepIconType.ENTERED_CALL) {
      indentation += 1;
    } else if (highlightData.icon === ReportStepIconType.RETURNING) {
      indentation -= 1;
    }

    items.push({
      id: ReportTreeKind.getId(ReportTreeKind.REPORT_STEPS, report, index),
      name: report.checkerMsg,
      kind: ReportTreeKind.REPORT_STEPS,
      step: step,
      report: report,
      icon: highlightData.icon,
      reportStepIcon: reportStepIcon,
      bgColor: highlightData.bgColor,
      level: indentation,
      fileName: fileName,
      shortFileName: shortFileName
    });
  });

  return items;
}

export default function formatReportDetails(report, reportDetails) {
  const items = [];

  // Add extended items such as notes and macros.
  const extendedItems = formatExtendedData(report, reportDetails.extendedData);
  items.push(...extendedItems);

  // Add main report node.
  items.push({
    id: ReportTreeKind.getId(ReportTreeKind.BUG, report),
    name: report.checkerMsg,
    kind: ReportTreeKind.BUG,
    report: report
  });

  const reportSteps = formatReportEvents(report, reportDetails.pathEvents);
  items.push(...reportSteps);

  return items;
}
