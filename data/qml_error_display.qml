import Qt 4.7

import com.nokia.meego 1.0
//import Qt.labs.components.native 1.0

PageStackWindow
{
	id: stackWindow

	initialPage: Page
	{
		id: titleScreenPage
	
		NotificationBar
		{
			id: notificationBar
		}
	
		Text
		{
			text: "Hello World!"
			font.bold: true
			font.pointSize: 30
			anchors.top: notificationBar.bottom
			anchors.topMargin: 10
			width: parent.width
			horizontalAlignment: Text.AlignHCenter
			verticalAlignment: Text.AlignVCenter
		}
	
	}

}
