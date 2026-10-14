import QtQuick 2.15
import QtQuick.Layouts 1.15
import org.kde.plasma.core 2.0 as PlasmaCore
import org.kde.plasma.components 3.0 as PlasmaComponents3
import org.kde.plasma.plasmoid 2.0

Item {
    id: root

    implicitWidth: 210
    implicitHeight: PlasmaCore.Units.iconSizes.smallMedium
    Layout.minimumWidth: 210
    Layout.preferredWidth: 210
    Layout.maximumWidth: 210

    property string cpuValue: "--"
    property string memoryValue: "--"
    property string temperatureValue: "--"
    property bool dataReady: false

    Plasmoid.preferredRepresentation: Plasmoid.compactRepresentation
    Plasmoid.toolTipMainText: "T3 Gemstone Sistem Durumu"
    Plasmoid.toolTipSubText: dataReady
        ? "CPU yükü: " + cpuValue + "%\nRAM kullanımı: " + memoryValue
          + "%\nCPU sıcaklığı: " + temperatureValue + " °C"
        : "Sistem değerleri okunuyor…"

    PlasmaCore.DataSource {
        id: statusSource
        engine: "executable"
        interval: 3000
        connectedSources: ["/usr/lib/t3-gemstone-theme/panel-status.sh"]

        onNewData: {
            var output = data["stdout"] || ""
            var fields = output.trim().split("|")
            if (fields.length === 3) {
                root.cpuValue = fields[0]
                root.memoryValue = fields[1]
                root.temperatureValue = fields[2]
                root.dataReady = true
            }
        }
    }

    PlasmaCore.DataSource {
        id: applicationLauncher
        engine: "executable"

        onNewData: disconnectSource(sourceName)
    }

    Plasmoid.compactRepresentation: MouseArea {
        id: compactRoot

        implicitWidth: 210
        implicitHeight: PlasmaCore.Units.iconSizes.smallMedium
        Layout.minimumWidth: 210
        Layout.preferredWidth: 210
        Layout.maximumWidth: 210
        hoverEnabled: true

        onClicked: {
            applicationLauncher.disconnectSource("/usr/bin/plasma-systemmonitor")
            applicationLauncher.connectSource("/usr/bin/plasma-systemmonitor")
        }

        Rectangle {
            anchors.fill: parent
            radius: PlasmaCore.Units.smallSpacing
            color: compactRoot.containsMouse
                ? PlasmaCore.Theme.highlightColor
                : "transparent"
            opacity: compactRoot.containsMouse ? 0.18 : 1.0
        }

        RowLayout {
            id: statusRow
            anchors.centerIn: parent
            spacing: PlasmaCore.Units.smallSpacing

            PlasmaCore.IconItem {
                source: "utilities-system-monitor"
                Layout.preferredWidth: PlasmaCore.Units.iconSizes.small
                Layout.preferredHeight: PlasmaCore.Units.iconSizes.small
                active: compactRoot.containsMouse
            }

            PlasmaComponents3.Label {
                text: "CPU " + root.cpuValue + "%"
                color: "#33d6ff"
                font.bold: true
                font.pointSize: PlasmaCore.Theme.smallestFont.pointSize
            }

            PlasmaComponents3.Label {
                text: "RAM " + root.memoryValue + "%"
                color: PlasmaCore.Theme.textColor
                font.pointSize: PlasmaCore.Theme.smallestFont.pointSize
            }

            PlasmaComponents3.Label {
                text: root.temperatureValue + "°C"
                color: Number(root.temperatureValue) >= 75 ? "#ff4d4d" : "#ffb020"
                font.bold: true
                font.pointSize: PlasmaCore.Theme.smallestFont.pointSize
            }
        }
    }
}
