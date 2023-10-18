@ECHO off

pushd "%~dp0"

ECHO   r::::::::::::::::::::::::::::::::::r
ECHO   :                                  :
ECHO   :               :PP.               :
ECHO   :               vBBr               :
ECHO   :               7BB:               :
ECHO   :               rBB:               :
ECHO   :      :DQRE:   rBB:   :gMBb:      :
ECHO   :       :BBBi   rBB:   7BBB.       :
ECHO   :        KBB:   rBB:   rBBI        :
ECHO   :        qBB:   rBB:   rQBU        :
ECHO   :        qBB:   rBB:   iBBS        :
ECHO   :        qBB:   iBB:   7BBj        :
ECHO   :        iBBY   iBB.   2BB.        :
ECHO   :         SBQq  iBQ:  EBBY         :
ECHO   :          :MQBZMBBDRBBP.          :
ECHO   :              .YBB7               :
ECHO   :               :BB.               :
ECHO   :               7BBi               :
ECHO   :               rBB:               :
ECHO   :                                  :
ECHO   r::::::::::::::::::::::::::::::::::r
ECHO:
ECHO                  hydrus
ECHO:

SET /P ready="This will download the latest exe installer using winget and install it to this location! As always, make a backup before you update. Hit Enter to start."

winget install --id=HydrusNetwork.HydrusNetwork  -e --location "./"

popd

SET /P done="Done!"
