#!/usr/bin/env python3

import asyncio
import websockets
from math import floor, ceil, pi, sin, cos, tan
from json import dumps as json
from time import time, sleep
from pycreate2 import Create2

DIAMETER = 235
CIRCUMFERENCE = DIAMETER * pi
STRAFE_SPEED = 342
LANE_WIDTH = 1117.6
LANE_LENGTH = 3073.4
TILT_SPEED = 171
GUTTER_TURN_SPEED = 171
MAX_TILT_ANGLE = 30
TURN_SPEED = 228
DRIVE_SPEED = 484.5
WEBSOCKET_HOST = '0.0.0.0'
WEBSOCKET_PORT = 8080

ws_clients = set()

class RoombaController:
    def __init__(self, port='/dev/ttyUSB0', baud=115200):
        self.bot = Create2(port, baud=baud)
        self.bot.start()
        self.bot.full()
        self.bot.drive_stop()
        self._bumped = False

    def __del__(self):
        del self.bot

    def strafe(self, stop=True):
        direction = 1
        self.bot.drive_straight(ceil(STRAFE_SPEED))
        prev_time = time()
        pos = 0.0
        while not self.is_bumped():
            now = time()
            pos += direction * (now - prev_time) * STRAFE_SPEED
            prev_time = now
            if pos >= LANE_WIDTH / 2 and direction != -1:
                self.bot.drive_straight(-ceil(STRAFE_SPEED))
                direction = -1
            elif pos <= -LANE_WIDTH / 2 and direction != 1:
                self.bot.drive_straight(ceil(STRAFE_SPEED))
                direction = 1
        if stop:
            self.bot.drive_stop()
        return -pos

    def angle(self, stop=True):
        direction = 1
        self.bot.drive_rotate(ceil(TILT_SPEED), 1)
        prev_time = time()
        pos = 0.0
        while not self.is_bumped():
            now = time()
            pos += direction * (now - prev_time) * (TILT_SPEED / (DIAMETER / 2) / pi * 180)
            prev_time = now
            if pos >= MAX_TILT_ANGLE and direction != -1:
                self.bot.drive_rotate(ceil(TILT_SPEED), -1)
                direction = -1
            elif pos <= -MAX_TILT_ANGLE and direction != 1:
                self.bot.drive_rotate(ceil(TILT_SPEED), 1)
                direction = 1
        if stop:
            self.bot.drive_stop()
        return -pos

    def wait_for_kick(self):
        while not self.is_bumped():
            pass

    def turn(self, angle, speed=TURN_SPEED, stop=True):
        direction = 1
        duration = angle * pi / 180 * (DIAMETER / 2) / TURN_SPEED
        if angle < 0:
            direction = -1
            duration = -duration
        self.bot.drive_rotate(ceil(speed), direction)
        sleep(duration)
        if stop:
            self.bot.drive_stop()

    def drive(self, distance, speed=DRIVE_SPEED, stop=True):
        if (distance < 0) != (speed < 0):
            speed = -speed
        self.bot.drive_straight(ceil(speed) if speed > 0 else floor(speed))
        sleep(distance / speed)
        if stop:
            self.bot.drive_stop()

    def is_bumped(self):
        sensors = self.bot.get_sensors().bumps_wheeldrops
        bumped = sensors.bump_left or sensors.bump_right
        rising_edge = bumped and not self._bumped
        self._bumped = bumped
        return rising_edge

async def publish(message):
    for client in ws_clients:
        await client.send(message)

async def relay(from_client, message):
    for client in ws_clients:
        if client is not from_client:
            await client.send(message)

async def on_connect(ws, path):
    ws_clients.add(ws)
    while True:
        try:
            message = await ws.recv()
        except websockets.ConnectionClosed:
            break
        else:
            await relay(ws, message)
    ws_clients.remove(ws)

async def main(port='/dev/ttyUSB0', baud=115200):
    await websockets.serve(on_connect, WEBSOCKET_HOST, WEBSOCKET_PORT)
    controller = RoombaController(port, baud)
    try:
        while True:
            await publish(json({'type': 'ready'}))
            print('Kick the Roomba to start.')
            await asyncio.get_event_loop().run_in_executor(None, controller.wait_for_kick)
            await publish(json({'type': 'waiting', 'next': 'strafe'}))
            print('Turning...')
            await asyncio.sleep(0.5)
            await asyncio.get_event_loop().run_in_executor(None, controller.turn, -90)
            await publish(json({'type': 'strafe'}))
            print('Strafing...')
            strafe_pos = await asyncio.get_event_loop().run_in_executor(None, controller.strafe)
            print('x-position: {}'.format(strafe_pos))
            await publish(json({'type': 'waiting', 'next': 'angle', 'strafePos': strafe_pos / (LANE_WIDTH / 2)}))
            print('Turning...')
            await asyncio.get_event_loop().run_in_executor(None, controller.turn, 90)
            await publish(json({'type': 'angle'}))
            print('Select angle...')
            angle = await asyncio.get_event_loop().run_in_executor(None, controller.angle)
            print('Angle: {}'.format(angle))

            pos_angle_rad = abs(angle) * pi / 180
            x_dist_to_gutter = (
                (LANE_WIDTH / 2) - strafe_pos if angle > 0
                else (LANE_WIDTH / 2) + strafe_pos
            )
            dist_to_gutter = x_dist_to_gutter / sin(pos_angle_rad)
            dist_to_end = LANE_LENGTH / cos(pos_angle_rad)
            predicted_gutter = dist_to_gutter < dist_to_end
            remaining_gutter = LANE_LENGTH - x_dist_to_gutter / tan(pos_angle_rad)

            await publish(json({'type': 'drive', 'heading': angle, 'predictedGutter': predicted_gutter}))
            print('Driving... (gutter prediction: {})'.format(predicted_gutter))
            if predicted_gutter:
                await asyncio.get_event_loop().run_in_executor(None, lambda: controller.drive(-dist_to_gutter, stop=False))
                await asyncio.get_event_loop().run_in_executor(None, lambda: controller.turn(angle, GUTTER_TURN_SPEED, stop=False))
                await asyncio.get_event_loop().run_in_executor(None, controller.drive, -remaining_gutter)
            else:
                await asyncio.get_event_loop().run_in_executor(None, controller.drive, -dist_to_end)
            await asyncio.sleep(1)
            await publish(json({'type': 'end'}))

            # reset
            if predicted_gutter:
                await asyncio.get_event_loop().run_in_executor(None, lambda: controller.drive(remaining_gutter, stop=False))
                await asyncio.get_event_loop().run_in_executor(None, lambda: controller.turn(-angle, GUTTER_TURN_SPEED, stop=False))
                await asyncio.get_event_loop().run_in_executor(None, controller.drive, dist_to_gutter)
            else:
                await asyncio.get_event_loop().run_in_executor(None, controller.drive, dist_to_end)
            controller.turn(angle, TILT_SPEED)
            controller.turn(-90)
            controller.drive(strafe_pos, STRAFE_SPEED)
            controller.turn(90)
    finally:
        await publish(json({'type': 'cancelled'}))
        print('Stopped.')
        del controller

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
    asyncio.get_event_loop().run_forever()
