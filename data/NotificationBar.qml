import Qt 4.7

import com.nokia.meego 1.0
//import Qt.labs.components.native 1.0

import "appTheme.js" as AppTheme

Rectangle
{
	id: errorDisplay
	color: AppTheme.errorBGColor
	visible: errorLog.hasMessages
	anchors.top: parent.top
	width: parent.width
	height: errorLog.hasMessages? 32 : 0

	Row
	{
		anchors.top: parent.top
		anchors.verticalCenter: parent.verticalCenter
		width: parent.width

		Image
		{
			anchors.verticalCenter: parent.verticalCenter
		}
		Text
		{
			text: errorLog.currentMessage.message
			color: AppTheme.errorFGColor
			elide: Text.ElideRight
			anchors.verticalCenter: parent.verticalCenter
			width: parent.width
			height: 32
		}
	}

	Text
	{
		text: "X"
		anchors.top: parent.top
		anchors.right: parent.right
		anchors.verticalCenter: parent.verticalCenter

		MouseArea
		{
			anchors.fill: parent
			onClicked: {errorLog.pop()}
		}
	}
}


