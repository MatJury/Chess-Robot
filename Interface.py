import PySimpleGUI as sg
import ChessLogic as cl
import time
import os
import copy
import threading
import time
import cv2
import sys
import json
import VisionModule as vm
import platform
#import ArmControl as ac
import lss_const as lssc
import pygame
import pathlib

try:
    from picamera.array import PiRGBArray
    from picamera import PiCamera
except:
    pass
    
'''
styles:

BlueMono
GreenTan
LightGreen
Black
Dark
'''

#   GLOBAL VARIABLES

CHESS_PATH = 'pieces_images'  # path to the chess pieces

BLANK = 0  # piece names
PAWNB = 1
KNIGHTB = 2
BISHOPB = 3
ROOKB = 4
KINGB = 5
QUEENB = 6
PAWNW = 7
KNIGHTW = 8
BISHOPW = 9
ROOKW = 10
KINGW = 11
QUEENW = 12

initial_board = [[ROOKB, KNIGHTB, BISHOPB, QUEENB, KINGB, BISHOPB, KNIGHTB, ROOKB],
                 [PAWNB, ] * 8,
                 [BLANK, ] * 8,
                 [BLANK, ] * 8,
                 [BLANK, ] * 8,
                 [BLANK, ] * 8,
                 [PAWNW, ] * 8,
                 [ROOKW, KNIGHTW, BISHOPW, QUEENW, KINGW, BISHOPW, KNIGHTW, ROOKW]]

psg_board = copy.deepcopy(initial_board)

blank = os.path.join(CHESS_PATH, 'blank.png')
bishopB = os.path.join(CHESS_PATH, 'nbishopb.png')
bishopW = os.path.join(CHESS_PATH, 'nbishopw.png')
pawnB = os.path.join(CHESS_PATH, 'npawnb.png')
pawnW = os.path.join(CHESS_PATH, 'npawnw.png')
knightB = os.path.join(CHESS_PATH, 'nknightb.png')
knightW = os.path.join(CHESS_PATH, 'nknightw.png')
rookB = os.path.join(CHESS_PATH, 'nrookb.png')
rookW = os.path.join(CHESS_PATH, 'nrookw.png')
queenB = os.path.join(CHESS_PATH, 'nqueenb.png')
queenW = os.path.join(CHESS_PATH, 'nqueenw.png')
kingB = os.path.join(CHESS_PATH, 'nkingb.png')
kingW = os.path.join(CHESS_PATH, 'nkingw.png')

images = {BISHOPB: bishopB, BISHOPW: bishopW, PAWNB: pawnB, PAWNW: pawnW, KNIGHTB: knightB, KNIGHTW: knightW,
          ROOKB: rookB, ROOKW: rookW, KINGB: kingB, KINGW: kingW, QUEENB: queenB, QUEENW: queenW, BLANK: blank}

wclock = os.getcwd() + '/interface_images/wclock.png'
bclock = os.getcwd() + '/interface_images/bclock.png'

graveyard = 'k0'
playerColor = True
playing =  False
blackSquareColor = '#B58863'
whiteSquareColor = '#F0D9B5'
Debug = False
sequence = []
state = "stby"
newGameState = "config"
gameTime = 60.00
playerSide = 0
route = os.getcwd() + '/'
homography = []
prevIMG = []
chessRoute = ""
detected = True
selectedCam = 0
skillLevel = 20     # difficulty level of chess engine
cap = cv2.VideoCapture()
rotMat = vm.np.zeros((2,2))
phisicalParams = {"baseradius": 0.00,
                    "cbFrame": 0.00,
                    "sqSize": 0.00,
                    "cbHeight": 0.00,
                    "pieceHeight": 0.00}

def systemConfig():
    global chessRoute

    if platform.system() == 'Windows':
        chessRoute = "games/stockfishX64.exe"
    elif platform.system() == 'Linux':
        chessRoute = "/usr/games/stockfish"

#   GAME FUNCTIONS

def pcTurn(board,engine):
    global sequence
    global state
    command = ""
    pcMove = engine.play(board, cl.chess.engine.Limit(time=1))
    sequence = cl.sequenceGenerator(pcMove.move.uci(), board)
    window.FindElement(key = "gameMessage").Update(sequence["type"])
    board.push(pcMove.move)
    #speakThread = threading.Thread(target=speak, args=[command], daemon=True)
    if board.is_checkmate():
        window.FindElement(key = "robotMessage").Update("CHECKMATE!")
        command = "checkmate"
        speakThread = threading.Thread(target=speak, args=[command], daemon=True)
        speakThread.start()
    elif board.is_check():
        window.FindElement(key = "robotMessage").Update("CHECK!")
        command = "check"
        speakThread = threading.Thread(target=speak, args=[command], daemon=True)
        speakThread.start()
    elif sequence["type"] == "White Queen Side Castling" or sequence["type"] == "Black Queen Side Castling":
        command = "qcastling"
        speakThread = threading.Thread(target=speak, args=[command], daemon=True)
        speakThread.start()
    elif sequence["type"] == "White King Side Castling" or sequence["type"] == "Black King Side Castling":
        command = "kcastling"
        speakThread = threading.Thread(target=speak, args=[command], daemon=True)
        speakThread.start()
    elif sequence["type"] == "Capture":
        command = "capture"
        speakThread = threading.Thread(target=speak, args=[command], daemon=True)
        speakThread.start()
    elif sequence["type"] == "Passant":
        command = "passant"
        speakThread = threading.Thread(target=speak, args=[command], daemon=True)
        speakThread.start()
    elif sequence["type"] == "Promotion":
        command = "promotion"
        speakThread = threading.Thread(target=speak, args=[command], daemon=True)
        speakThread.start()

    #ac.executeMove(sequence["seq"],phisicalParams, playerColor)
    state = "robotMove"
    updateBoard(window, sequence)

def startEngine():
    global engine
    global state
    print ("startEngine")
    engine = cl.chess.engine.SimpleEngine.popen_uci(chessRoute)
    engine.configure({"Skill Level": skillLevel})
    if playerColor:
        state = "playerTurn"
    else:
        state = "pcTurn"

def playerTurn(board,squares):
    result = cl.moveAnalysis(squares, board)
    piece = ""
    if result:
        if result["type"] == "Promotion":
            while not piece:
                piece = coronationWindow()
            result["move"] += piece
        sequence = cl.sequenceGenerator(result["move"], board)
        window.FindElement(key = "gameMessage").Update(sequence["type"])
        board.push_uci(result["move"])
        updateBoard(window, sequence)
        return True
    else:
        return False

def startGame():
    global psg_board
    window.FindElement("newGame").Update(disabled=True)
    window.FindElement("quit").Update(disabled=False)
    psg_board = copy.deepcopy(initial_board)
    redrawBoard()

def quitGame():
    window.FindElement("newGame").Update(disabled=False)
    window.FindElement("quit").Update(disabled=True)

#   INTERFACE FUNCTIONS

def renderSquare(image, key, location):
    if (location[0] + location[1]) % 2:
        color =  blackSquareColor
    else:
        color = whiteSquareColor
    return sg.Button('', image_filename=image, size=(1, 1),
                          border_width=0, button_color=('white', color),
                          pad=(0, 0), key=key)

def redrawBoard():
    columns = 'abcdefgh'
    global playerColor
    if playerColor:
        for i in range(8):
            window.FindElement(key = str(8-i)+"r").Update("   "+str(8-i))
            window.FindElement(key = str(8-i)+"l").Update(str(8-i)+"   ")
            for j in range(8):
                window.FindElement(key = columns[j]+"t").Update(columns[j])
                window.FindElement(key = columns[j]+"b").Update(columns[j])    
                color = blackSquareColor if (i + j) % 2 else whiteSquareColor
                piece_image = images[initial_board[i][j]]
                elem = window.FindElement(key=(i, j))
                elem.Update(button_color=('white', color),
                            image_filename=piece_image, )
    else:
        for i in range(8):
            window.FindElement(key = str(8-i)+"r").Update("   "+str(i+1))
            window.FindElement(key = str(8-i)+"l").Update(str(i+1)+"   ")
            for j in range(8):
                window.FindElement(key = columns[j]+"t").Update(columns[7-j])
                window.FindElement(key = columns[j]+"b").Update(columns[7-j]) 
                color = blackSquareColor if (i + j) % 2 else whiteSquareColor
                piece_image = images[initial_board[7-i][7-j]]
                elem = window.FindElement(key=(i, j))
                elem.Update(button_color=('white', color),
                            image_filename=piece_image, )

def updateBoard(window, move):
    global playerColor
    for cont in range(0,len(move["seq"]),4):
        squareCleared = move["seq"][cont:cont+2]
        squareOcuped = move["seq"][cont+2:cont+4]
        y = cl.chess.square_file(cl.chess.SQUARE_NAMES.index(squareCleared))
        x = 7 - cl.chess.square_rank(cl.chess.SQUARE_NAMES.index(squareCleared))

        piece_image = images[psg_board[x][y]] 
        piece = psg_board[x][y]
        psg_board[x][y] = BLANK
        color = blackSquareColor if (x + y) % 2 else whiteSquareColor
        if playerColor:
            elem = window.FindElement(key=(x, y))
        else:
            elem = window.FindElement(key=(7-x, 7-y))
        elem.Update(button_color=('white', color),
                    image_filename=blank, )  

        if squareOcuped != graveyard:
            y = cl.chess.square_file(cl.chess.SQUARE_NAMES.index(squareOcuped))
            x = 7 - cl.chess.square_rank(cl.chess.SQUARE_NAMES.index(squareOcuped))
            psg_board[x][y] = piece
            color = blackSquareColor if (x + y) % 2 else whiteSquareColor
            if playerColor:
                elem = window.FindElement(key=(x, y))
            else:
                elem = window.FindElement(key=(7-x, 7-y))    
            elem.Update(button_color=('white', color),
                        image_filename=piece_image, )         

def sideConfig(): #gameState: sideConfig
    global newGameState
    global state
    global playerSide
    global prevIMG
    global rotMat
    global playerColor
    
    i = 0

    img = vm.drawQuadrants(prevIMG)
    imgbytes = cv2.imencode('.png', img)[1].tobytes()

    windowName = "Calibration"
    initGame = [[sg.Text('Please, choose the white side', justification='center', pad = (25,(5,15)), font='Any 15')],
                [sg.Image(data=imgbytes, key='boardImg')],
                [sg.Radio('1-2', group_id='grp', default = True,font='Any 14'), sg.Radio('2-3', group_id='grp',font='Any 14'),sg.Radio('4-3', group_id='grp',font='Any 14'), sg.Radio('1-4', group_id='grp',font='Any 14')],
                [sg.Text('_'*30)],
                [sg.Button("Back"), sg.Submit("Play")]]
    newGameWindow = sg.Window(windowName, default_button_element_size=(12,1), auto_size_buttons=False, location = (100,50), icon='kingb.ico').Layout(initGame) 

    while True:
        button,value = newGameWindow.Read(timeout=100)
        
        if button == "Play":
            newGameState = "initGame"
            while value[i] == False and i<4:
                i+=1
            playerSide = i
            if playerSide == 0:
                theta = -90
            elif playerSide == 1:
                theta = 180
            elif playerSide == 2:
                theta = 90
            elif  playerSide == 3:
                theta = 0
            if not playerColor:
                theta += 180
            rotMat = vm.findRotation(theta)
            prevIMG = vm.applyRotation(prevIMG,rotMat)
            break
        if button == "Back":
            newGameState = "ocupiedBoard"
            break
        if button in (None, 'Exit'): #MAIN WINDOW
            state = "stby"
            newGameState = "config"
            break   

    newGameWindow.close()

def ocupiedBoard(): #gameState: ocupiedBoard
    global newGameState
    global state
    global selectedCam
    global homography
    global prevIMG

    windowName = "Calibration"
    initGame = [[sg.Text('Please, place the chess pieces and press NEXT', justification='center', pad = (25,(5,15)), font='Any 15')],
                [sg.Image(filename='', key='boardVideo')],
                [sg.Text('_'*30)],
                [sg.Button("Back"), sg.Submit("Next")]]
    newGameWindow = sg.Window(windowName, default_button_element_size=(12,1), auto_size_buttons=False, location = (100,50), icon='kingb.ico').Layout(initGame)  

    while True:
        button,value = newGameWindow.Read(timeout = 10)

        if detected:    
            frame = takePIC()
            prevIMG = vm.applyTransformations(frame,homography,rotMat)
            imgbytes = cv2.imencode('.png', prevIMG)[1].tobytes()
            newGameWindow.FindElement('boardVideo').Update(data=imgbytes)

        if button == "Next":
            newGameState = "sideConfig"
            break
        if button == "Back":
            newGameState = "calibration"
            break
        if button in (None, 'Exit'): # MAIN WINDOW
            state = "stby"
            newGameState = "config"
            break   

    newGameWindow.close()

def calibration(): # gameState: calibration
    global newGameState
    global state
    global selectedCam
    global homography
    global detected
    global selectedCam

    cbPattern = cv2.imread(route+'interface_images/cb_pattern.jpg', cv2.IMREAD_GRAYSCALE)

    windowName = "Camera calibration"
    initGame = [[sg.Text('Please, adjust your camera and remove any chess piece', justification='center', pad = (25,(5,15)), font='Any 15', key = "calibrationBoard")],
                [sg.Image(filename='', key='boardVideo')],
                [sg.Text('_'*30)],
                [sg.Button("Back"), sg.Submit("Next")]]
    newGameWindow = sg.Window(windowName, default_button_element_size=(12,1), auto_size_buttons=False, location = (100,50), icon='kingb.ico').Layout(initGame) 

    while True:
        button,value = newGameWindow.Read(timeout = 10)

        if detected:    
            frame = takePIC()
            imgbytes = cv2.imencode('.png', frame)[1].tobytes()  
            newGameWindow.FindElement('boardVideo').Update(data=imgbytes)
            
            retIMG, homography = vm.findTransformation(frame,cbPattern)
            if retIMG:
                newGameWindow.FindElement('calibrationBoard').Update("Camera calibration successful, press NEXT")
            else:
                newGameWindow.FindElement('calibrationBoard').Update("Please adjust your camera and remove any chess piece")

        if button == "Next" and retIMG:
            newGameState = "ocupiedBoard"
            break
        if button == "Back":
            newGameState = "config"
            break
        if button in (None, 'Exit'):        # MAIN WINDOW
            state = "stby"
            newGameState = "config"
            break   

    newGameWindow.close() 

def newGameWindow (): #gameState: config
    global playerColor
    global gameTime
    global newGameState
    global state
    global detected
    global cap
    global selectedCam
    global skillLevel
    i = 0

    windowName = "Configuration"
    initGame = [[sg.Text('Game Parameters', justification='center', pad = (25,(5,15)), font='Any 15')],
                [sg.CBox('Play As White', key='userWhite', default = playerColor)],
                [sg.Spin([sz for sz in range(1, 300)], initial_value=10, font='Any 11',key='timeInput'),sg.Text('Time in minutes', pad=(0,0))],
                [sg.Radio('RPi Cam', group_id='grp', default = True), sg.Radio('USB Cam', group_id='grp')],
                [sg.Combo([sz for sz in range(0, 11)], key="enginelevel"),sg.Text('Engine Skill Level', pad=(0,0))],
                [sg.Text('_'*30)],
                [sg.Button("Exit"), sg.Submit("Next")]]
    windowNewGame = sg.Window(windowName, default_button_element_size=(12,1), auto_size_buttons=False, icon='kingb.ico').Layout(initGame)
    while True:
        button,value = windowNewGame.Read()
        if button == "Next":
            while value[i] == False and i<2:
                i+=1
            selectedCam = i
            #cap = initCam(i)
            if detected:
                newGameState = "calibration" 
                newGameState = "initGame"
                playerColor = value["userWhite"]
                skillLevel = value["enginelevel"]*2
                print(skillLevel)
                gameTime = float(value["timeInput"]*60)
            break
        if button in (None, 'Exit'): # MAIN WINDOW
            state = "stby"
            break   
    windowNewGame.close() 

def coronationWindow (): #gameState: config
    global playerColor
    pieceSelected = ""
    rook = rookB
    knight = knightB
    bishop = bishopB
    queen = queenB
    if playerColor:
        rook = rookW
        knight = knightW
        bishop = bishopW
        queen = queenW

    windowName = "Promotion"
    pieceSelection = [[sg.Text('Select the piece for promotion', justification='center', pad = (25,(5,15)), font='Any 15')],
                [sg.Button('', image_filename=rook, size=(1, 1),
                          border_width=0, button_color=('white', "brown"),
                          pad=((40,0), 0), key="rook"),sg.Button('', image_filename=knight, size=(1, 1),
                          border_width=0, button_color=('white', "brown"),
                          pad=(0, 0), key="knight"),sg.Button('', image_filename=bishop, size=(1, 1),
                          border_width=0, button_color=('white', "brown"),
                          pad=(0, 0), key="bishop"),sg.Button('', image_filename=queen, size=(1, 1),
                          border_width=0, button_color=('white', "brown"),
                          pad=(0, 0), key="queen")]]
    windowNewGame = sg.Window(windowName, default_button_element_size=(12,1), auto_size_buttons=False, icon='kingb.ico').Layout(pieceSelection)
    while True:
        button,value = windowNewGame.Read()
        if button == "rook":
            pieceSelected = "r"
            break
        if button == "knight":
            pieceSelected = "k"
            break
        if button == "bishop":
            pieceSelected = "b"
            break
        if button == "queen":
            pieceSelected = "q"
            break
        if button in (None, 'Exit'): # MAIN WINDOW
            break   
    windowNewGame.close() 
    return pieceSelected

def takePIC():  
    global selectedCam

    if selectedCam:
        for i in range(5):                    # Clear images stored in buffer
            cap.grab()
        ret, frame = cap.read()               # USB Cam
    else:
        cap.capture(rawCapture, format="bgr") # RPi Cam
        frame = rawCapture.array
        rawCapture.truncate(0)                # Clear the stream in preparation for the next image
    
    return frame

def quitGameWindow ():
    global playing
    global window
    windowName = "Quit Game"
    quitGame = [[sg.Text('Are you sure?',justification='center', size=(30, 1), font='Any 13')], [sg.Submit("Yes",  size=(15, 1)),sg.Submit("No", size=(15, 1))]]
    if playing:
        while True:
            windowNewGame = sg.Window(windowName, default_button_element_size=(12,1), auto_size_buttons=False, icon='kingb.ico').Layout(quitGame)
            button,value = windowNewGame.Read()
            if button == "Yes":
                playing = False
                break
            if button in (None, 'Exit', "No"): # MAIN WINDOW
                break   
    windowNewGame.close()   

def mainBoardLayout():
    # ------ Menu Definition ------ #      
    menu_def = [['&File',["&Parameters","E&xit"]],      
                ['&Help', 'About...'], ]  

    # ------ Layout ------ # 
    # sg.SetOptions(margins=(0,0))
    sg.ChangeLookAndFeel('Dark')
    # Create initial board setup
    board = copy.deepcopy(initial_board)
    # Main board display layout
    board_layout = [[sg.T(' '*12)] + [sg.T('{}'.format(a), pad=((0,47),0), font='Any 13', key = a+'t') for a in 'abcdefgh']]
    # Loop though board and create buttons with images
    for i in range(8):
        numberRow = 8-i 
        row = [sg.T(str(numberRow)+'   ', font='Any 13', key = str(numberRow)+"l")]
        for j in range(8):
            piece_image = images[board[i][j]]
            row.append(renderSquare(piece_image, key=(i,j), location=(i,j)))
        row.append(sg.T('   '+str(numberRow), font='Any 13', key = str(numberRow)+"r"))
        board_layout.append(row)
    # Add labels across bottom of board
    board_layout.append([sg.T(' '*12)] + [sg.T('{}'.format(a), pad=((0,47),0), font='Any 13', key = a+'b') for a in 'abcdefgh'])

    frame_layout_game = [
                [sg.Button('---', size=(14, 2), border_width=0,  font=('courier', 16), button_color=('black', "white"), pad=(4, 4), key="gameMessage")],
               ]
    frame_layout_robot = [
                [sg.Button('---', size=(14, 2), border_width=0,  font=('courier', 16), button_color=('black', "white"), pad=(4, 4), key="robotMessage")],
                ]
    board_controls = [[sg.RButton('New Game', key='newGame', size=(15, 2), pad=(0,(0,7)), font=('courier', 16))],
                        [sg.RButton('Quit', key='quit', size=(15, 2), pad=(0, 0), font=('courier', 16), disabled = True)],
                        [sg.Frame('GAME', frame_layout_game, pad=(0, 10), font='Any 12', title_color='white', key = "frameMessageGame")],
                        [sg.Frame('ROBOT', frame_layout_robot, pad=(0, (0,10)), font='Any 12', title_color='white', key = "frameMessageRobot")],
                        [sg.Button('White Time', size=(7, 2), border_width=0,  font=('courier', 16), button_color=('black', whiteSquareColor), pad=(0, 0), key="wt"),sg.Button('Black Time',  font=('courier', 16), size=(7, 2), border_width=0, button_color=('black', blackSquareColor), pad=((7,0), 0), key="bt")],
                        [sg.T("00:00:00",size=(9, 2), font=('courier', 13),key="wcount",pad = ((4,0),0)),sg.T("00:00:00",size=(9, 2), pad = (0,0), font=('courier', 13),key="bcount")],
                        [sg.Button('', image_filename=wclock, key='clockButton', pad = ((25,0),0))]]

    layout = [[sg.Menu(menu_def, tearoff=False, key="manubar")], 
                [sg.Column(board_layout),sg.VerticalSeparator(pad=None),sg.Column(board_controls)]]

    return layout

def initCam(selectedCam):
    global detected
    global rawCapture

    button, value = window.Read(timeout=10)
    if selectedCam: # USB Cam
        cap = cv2.VideoCapture(1)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT,480)
        if not cap.isOpened():
            detected = False  
            sg.popup_error('USB Video device not found')
    else:           # RPi Cam
        cap = PiCamera()
        if not cap:
            detected = False    
            sg.popup_error('RPi Video device not found')
        else:
            cap.resolution = (640, 480)
            rawCapture = PiRGBArray(cap, size=(640, 480))
    return cap

def loadParams():
    global phisicalParams

    if os.path.isfile('params.txt'):
        json_file = open('params.txt')
        phisicalParams = json.load(json_file)
        print(json_file)
    else:
        outfile = open('params.txt', 'w')
        json.dump(phisicalParams, outfile)

def phisicalConfig ():
    global phisicalParams
    
    windowName = "Robot parameters"
    robotParamLayout= [[sg.Text('Insert the phisical dimentions in inches',justification='center', font='Any 14', pad=(10,10))], 
                       [sg.Spin([sz/100 for sz in range(1, 1000)], initial_value=phisicalParams["baseradius"], font='Any 11'),sg.Text('Base Radius', pad=(0,0))],
                        [sg.Spin([sz/100 for sz in range(1, 1000)], initial_value=phisicalParams["cbFrame"], font='Any 11'),sg.Text('Chess Board Frame', pad=(0,0))],
                        [sg.Spin([sz/100 for sz in range(1, 1000)], initial_value=phisicalParams["sqSize"], font='Any 11'),sg.Text('Square Size', pad=(0,0))],
                        [sg.Spin([sz/100 for sz in range(1, 1000)], initial_value=phisicalParams["cbHeight"], font='Any 11'),sg.Text('Chess Board Height', pad=(0,0))],
                        [sg.Spin([sz/100 for sz in range(1, 1000)], initial_value=phisicalParams["pieceHeight"], font='Any 11'),sg.Text('Tallest Piece Height', pad=(0,0))],
                        [sg.Text('_'*37)],
                        [sg.Submit("Save",  size=(15, 1)),sg.Submit("Close", size=(15, 1))]]

    while True:
        robotParamWindow = sg.Window(windowName, default_button_element_size=(12,1), auto_size_buttons=False, icon='kingb.ico').Layout(robotParamLayout)
        button,value = robotParamWindow.Read()
        if button == "Save":
            phisicalParams = {"baseradius": value[0],
                    "cbFrame":value[1],
                    "sqSize": value[2],
                    "cbHeight":value[3],
                    "pieceHeight": value[4]}
            outfile = open('params.txt', 'w')
            json.dump(phisicalParams, outfile)
            break
        if button in (None, 'Close'): #MAIN WINDOW
            break   

    robotParamWindow.close()   

layout = mainBoardLayout()
window = sg.Window('ChessRobot', default_button_element_size=(12,1), auto_size_buttons=False, icon='kingb.ico').Layout(layout)

def speak(command):
    pygame.mixer.init()
    filePath = str(pathlib.Path().absolute())+"/audio/"
    if command == "capture":
        pygame.mixer.music.load(filePath+"capture.mp3")
    elif command == "kcastling":
        pygame.mixer.music.load(filePath+"k_castling.mp3")
    elif command == "qcastling":
        pygame.mixer.music.load(filePath+"q_castling.mp3")
    elif command == "passant":
        pygame.mixer.music.load(filePath+"passant.mp3")
    elif command == "promotion":
        pygame.mixer.music.load(filePath+"promotion.mp3")
    elif command == "check":
        pygame.mixer.music.load(filePath+"check.mp3")
    elif command == "checkmate":
        pygame.mixer.music.load(filePath+"checkmate.mp3")
    elif command == "excuse":
        pygame.mixer.music.load(filePath+"excuse.mp3")
    elif command == "please":
        pygame.mixer.music.load(filePath+"please.mp3")
    pygame.mixer.music.play()

def main():
    global playerColor
    global state
    global playing
    global sequence
    global newGameState
    global detected
    global phisicalParams
    global moveState
    global prevIMG
    global rotMat

    systemConfig()
    loadParams()
    interfaceMessage = ""
    board = cl.chess.Board()
    squares = []
    whiteTime = 0
    blackTime = 0
    refTime = time.time()

    while True :
        button, value = window.Read(timeout=100)

        if button in (None, 'Exit') or value["manubar"]=="Exit": # MAIN WINDOW
            break

        if value["manubar"]=="Parameters":
            if playing:
                sg.popup("Please, first quit the game")
            else:
                phisicalConfig()

        if button =="newGame":
            if phisicalParams["baseradius"] and phisicalParams["cbFrame"] and phisicalParams["sqSize"] and phisicalParams["cbHeight"] and phisicalParams["pieceHeight"]: 
                print("entro en new")
                state = "startMenu"
            else:
                sg.popup_error('Please configure the robot parameters in the File/Parameters option of menu bar')

        if button =="quit":
            print("entro en quit")
            quitGameWindow()
            if not playing:
                state = "showGameResult"

        #machine messages
        if playing:
            if board.is_game_over():
                playing = False
                print("GAME OVER")
                state = "showGameResult"
            elif  whiteTime <= 0:
                playing = False
                print("GAME OVER")
                state = "showGameResult"
                window.FindElement(key = "gameMessage").Update("Time Out\n"+"Black Wins")
            elif  blackTime <= 0:
                playing = False
                print("GAME OVER")
                state = "showGameResult"
                window.FindElement(key = "gameMessage").Update("Time Out\n"+ "White Wins")

        if state == "stby": #stby
            print(state)

        elif state == "startMenu": #Start Menu
            print(state)
            if newGameState == "config":
                newGameWindow()
            elif newGameState == "calibration":
                calibration()
            elif newGameState == "ocupiedBoard":
                ocupiedBoard()
            elif newGameState == "sideConfig":
                sideConfig()
            elif newGameState == "initGame":
                playing = True
                newGameState = "config"
                startGame()
                board = cl.chess.Board()
                window.FindElement(key = "wcount").Update(time.strftime("%H:%M:%S", time.gmtime(gameTime)))
                window.FindElement(key = "bcount").Update(time.strftime("%H:%M:%S", time.gmtime(gameTime)))
                window.FindElement(key = "clockButton").Update(image_filename=wclock)
                window.FindElement(key = "robotMessage").Update("Good Luck!")
                whiteTime = gameTime
                blackTime = gameTime
                refTime = time.time()
                startEngineThread = threading.Thread(target=startEngine, daemon=True)
                startEngineThread.start()
                state = "stby"
                
        elif state == "playerTurn": #Player Turn
#             print(state)
            if button == "clockButton":
                currentIMG = takePIC()
                curIMG = vm.applyTransformations(currentIMG,homography,rotMat)
                squares = vm.findMoves(prevIMG, curIMG)
                print(squares)
                if playerTurn(board, squares):
                    state = "pcTurn"
                else:
                    window.FindElement(key = "gameMessage").Update("Invalid move!")
                    state = "playerTurn"
        
        elif state == "pcTurn": # PC turn
            print(state)
            
            if board.turn:
                window.FindElement(key = "clockButton").Update(image_filename=wclock)
            else:
                window.FindElement(key = "clockButton").Update(image_filename=bclock)
                
            pcTurnThread = threading.Thread(target=pcTurn, args=(board,engine,), daemon=True)
            pcTurnThread.start()
            state = "stby"         # Wait for the PC move, thread changes the state

        elif state == "robotMove": # Robotic arm turn
            print(state)
            previousIMG = takePIC()
            prevIMG = vm.applyTransformations(previousIMG,homography,rotMat)
            state = "playerTurn"
            window.FindElement(key = "robotMessage").Update("---")
            if board.turn:
                window.FindElement(key = "clockButton").Update(image_filename=wclock)
            else:
                window.FindElement(key = "clockButton").Update(image_filename=bclock)

        elif state == "showGameResult":
            print(state)
            gameResult = board.result()
            if gameResult == "1-0":
                window.FindElement(key = "gameMessage").Update("Game Over" + "\nWhite Wins")
                # if not playerColor:    # If the player color is black -> robot color is white
                #     ac.winLED(ac.allMotors)
            elif gameResult == "0-1":
                window.FindElement(key = "gameMessage").Update("Game Over" + "\nBlack Wins")
                # if playerColor:        # If the player color is white -> robot color is black
                #     ac.winLED(ac.allMotors)
            elif gameResult == "1/2-1/2":
                window.FindElement(key = "gameMessage").Update("Game Over" + "\nDraw")
            quitGame()
            engine.quit()
            state = "stby"
            
        if playing:
            dt = time.time() - refTime
            if board.turn:
                whiteTime = whiteTime - dt
                if whiteTime < 0:
                    whiteTime = 0
                refTime = time.time()
                window.FindElement(key = "wcount").Update(time.strftime("%H:%M:%S", time.gmtime(whiteTime)))
            else:
                blackTime = blackTime - dt
                if blackTime < 0:
                    blackTime = 0
                refTime = time.time()
                window.FindElement(key = "bcount").Update(time.strftime("%H:%M:%S", time.gmtime(blackTime)))

    window.close() 
    

if __name__ == "__main__":
    main()

