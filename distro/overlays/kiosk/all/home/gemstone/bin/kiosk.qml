// Gemstone Example Control Station -- UI for bin/kiosk.
//
// Everything here is drawn by the Qt Quick scene graph, which means OpenGL.
// Canvas is deliberately not used: its default render target paints with
// QPainter into an image that is then uploaded as a texture, the same path that
// comes out black on the PowerVR driver. QtQuick.Shapes strokes the traces on
// the GPU instead.

import QtQuick 2.15
import QtQuick.Window 2.15
import QtQuick.Layouts 1.15
import QtQuick.Shapes 1.15

Window {
    id: root

    readonly property color accent: "#00CED1"  // turkuaz
    readonly property color warn: "#FF4500"    // kirmizimsi turuncu
    readonly property color ok: "#00FF00"

    visible: true
    width: 800
    height: 480
    visibility: Window.FullScreen
    color: "black"
    title: "Gemstone Example Control Station"

    // A labelled bar with its current value, as used for all three readouts.
    component Gauge: ColumnLayout {
        id: gauge

        property string label
        property real value
        property real maximum
        property color barColor

        spacing: 6
        Layout.fillWidth: true

        Text {
            text: gauge.label
            color: gauge.barColor
            font.pixelSize: 15
            Layout.alignment: Qt.AlignHCenter
        }

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 32
            color: "black"
            radius: 5
            border.width: 2
            border.color: gauge.barColor

            Rectangle {
                anchors {
                    left: parent.left
                    top: parent.top
                    bottom: parent.bottom
                    margins: 2
                }
                width: Math.max(0, (parent.width - 4) * Math.min(1, gauge.value / gauge.maximum))
                radius: 3
                color: gauge.barColor
            }

            Text {
                anchors.centerIn: parent
                text: Math.round(gauge.value)
                color: "white"
                font.pixelSize: 15
            }
        }
    }

    // A flat button. The example does not wire these to anything.
    component ActionButton: Rectangle {
        id: button

        property alias text: buttonLabel.text

        Layout.fillWidth: true
        implicitHeight: 44
        radius: 5

        Text {
            id: buttonLabel
            anchors.centerIn: parent
            color: "black"
            font.pixelSize: 18
        }

        MouseArea {
            anchors.fill: parent
            onPressed: button.opacity = 0.7
            onReleased: button.opacity = 1.0
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 10

        Text {
            text: "T3 Foundation Gemstone Project"
            color: root.accent
            font.pixelSize: 26
            font.bold: true
            Layout.alignment: Qt.AlignHCenter
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            Gauge {
                label: "Altitude (m)"
                value: telemetry.altitude
                maximum: 1000
                barColor: root.accent
            }
            Gauge {
                label: "Speed (m/s)"
                value: telemetry.speed
                maximum: 100
                barColor: root.warn
            }
            Gauge {
                label: "Battery (%)"
                value: telemetry.battery
                maximum: 100
                barColor: root.accent
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "black"
            border.width: 1
            border.color: Qt.darker(root.accent, 2.5)

            Text {
                id: plotTitle
                anchors {
                    top: parent.top
                    topMargin: 4
                    horizontalCenter: parent.horizontalCenter
                }
                text: "UAV Telemetry Data"
                color: root.accent
                font.pixelSize: 17
            }

            Item {
                id: plot

                anchors {
                    fill: parent
                    topMargin: plotTitle.height + 8
                    margins: 8
                }

                property int capacity: 100
                property var altitudeSamples: []
                property var speedSamples: []
                property var batterySamples: []

                property var altitudePath: []
                property var speedPath: []
                property var batteryPath: []

                // Each trace is plotted as a percentage of its own range, so all
                // three stay on screen: altitude runs to 1000, the others to 100.
                function append(samples, value) {
                    samples.push(value)
                    if (samples.length > capacity)
                        samples.shift()
                    return samples
                }

                function toPath(samples) {
                    var points = []
                    for (var i = 0; i < samples.length; ++i) {
                        points.push(Qt.point(plot.width * i / (plot.capacity - 1),
                                             plot.height * (1 - samples[i] / 100)))
                    }
                    return points
                }

                Repeater {
                    model: 4
                    Rectangle {
                        width: plot.width
                        height: 1
                        y: plot.height * (index + 1) / 5
                        color: Qt.darker(root.accent, 4.0)
                    }
                }

                Shape {
                    anchors.fill: parent
                    // The traces redraw ten times a second; keeping the geometry
                    // on the GPU avoids re-tessellating every frame.
                    asynchronous: false

                    ShapePath {
                        strokeColor: root.accent
                        strokeWidth: 2
                        fillColor: "transparent"
                        PathPolyline { path: plot.altitudePath }
                    }
                    ShapePath {
                        strokeColor: root.warn
                        strokeWidth: 2
                        fillColor: "transparent"
                        PathPolyline { path: plot.speedPath }
                    }
                    ShapePath {
                        strokeColor: root.ok
                        strokeWidth: 2
                        fillColor: "transparent"
                        PathPolyline { path: plot.batterySamples.length > 1 ? plot.batteryPath : [] }
                    }
                }

                Connections {
                    target: telemetry
                    function onUpdated() {
                        plot.append(plot.altitudeSamples, telemetry.altitude / 10)
                        plot.append(plot.speedSamples, telemetry.speed)
                        plot.append(plot.batterySamples, telemetry.battery)

                        plot.altitudePath = plot.toPath(plot.altitudeSamples)
                        plot.speedPath = plot.toPath(plot.speedSamples)
                        plot.batteryPath = plot.toPath(plot.batterySamples)
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            ActionButton {
                text: "Takeoff"
                color: root.accent
            }
            ActionButton {
                text: "Land"
                color: root.warn
            }
        }
    }
}
