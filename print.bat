@echo off
REM Usage: print.bat "C:\OdooPOS\PDFtoPrinter.exe" "C:\Users\odoo_test\Desktop\test.pdf" "FACTURE"

set "PDFTOPRINTER=%~1"
set "PDF_FILE=%~2"
set "PRINTER=%~3"

REM Affichage détaillé pour debug
echo ========== INFORMATIONS DE DÉBOGAGE ==========
echo Date et heure: %date% %time%
echo.
echo Paramètres reçus:
echo 1. PdftoPrinter: %PDFTOPRINTER%
echo 2. Fichier PDF: %PDF_FILE%
echo 3. Imprimante: %PRINTER%
echo.
echo Vérification des fichiers:
if exist "%PDFTOPRINTER%" (
    echo - PdftoPrinter.exe existe
) else (
    echo - ERREUR: PdftoPrinter.exe n'existe pas à l'emplacement spécifié
)

if exist "%PDF_FILE%" (
    echo - Le fichier PDF existe
) else (
    echo - ERREUR: Le fichier PDF n'existe pas à l'emplacement spécifié
)
echo.
echo Commande complète qui sera exécutée:
echo "%PDFTOPRINTER%" "%PDF_FILE%" "%PRINTER%"
echo ============================================
echo.

REM Exécution avec différentes options de ligne de commande
echo.
echo ========== TENTATIVES D'IMPRESSION ==========

echo Tentative 1: Commande standard
echo Commande: "%PDFTOPRINTER%" "%PDF_FILE%" "%PRINTER%"
"%PDFTOPRINTER%" "%PDF_FILE%" "%PRINTER%"
set ERRORLEVEL_1=%ERRORLEVEL%
echo Code de retour: %ERRORLEVEL_1%
if %ERRORLEVEL_1% == 0 (
    echo Impression réussie avec la commande standard!
) else (
    echo Échec de l'impression avec la commande standard (code %ERRORLEVEL_1%)
    
    echo.
    echo Tentative 2: Avec guillemets simples pour l'imprimante
    echo Commande: "%PDFTOPRINTER%" "%PDF_FILE%" %PRINTER%
    "%PDFTOPRINTER%" "%PDF_FILE%" %PRINTER%
    set ERRORLEVEL_2=%ERRORLEVEL%
    echo Code de retour: %ERRORLEVEL_2%
    if %ERRORLEVEL_2% == 0 (
        echo Impression réussie avec guillemets simples!
    ) else (
        echo Échec de l'impression avec guillemets simples (code %ERRORLEVEL_2%)
        
        echo.
        echo Tentative 3: Sans guillemets pour l'imprimante
        echo Commande: "%PDFTOPRINTER%" "%PDF_FILE%" %PRINTER:"=%
        "%PDFTOPRINTER%" "%PDF_FILE%" %PRINTER:"=%
        set ERRORLEVEL_3=%ERRORLEVEL%
        echo Code de retour: %ERRORLEVEL_3%
        if %ERRORLEVEL_3% == 0 (
            echo Impression réussie sans guillemets!
        ) else (
            echo Échec de l'impression sans guillemets (code %ERRORLEVEL_3%)
            
            echo.
            echo Tentative 4: Avec option -s (silencieux)
            echo Commande: "%PDFTOPRINTER%" -s "%PDF_FILE%" "%PRINTER%"
            "%PDFTOPRINTER%" -s "%PDF_FILE%" "%PRINTER%"
            set ERRORLEVEL_4=%ERRORLEVEL%
            echo Code de retour: %ERRORLEVEL_4%
            if %ERRORLEVEL_4% == 0 (
                echo Impression réussie avec option -s!
            ) else (
                echo Échec de l'impression avec option -s (code %ERRORLEVEL_4%)
                
                echo.
                echo Tentative 5: Avec option -p (imprimante par défaut)
                echo Commande: "%PDFTOPRINTER%" -p "%PDF_FILE%"
                "%PDFTOPRINTER%" -p "%PDF_FILE%"
                set ERRORLEVEL_5=%ERRORLEVEL%
                echo Code de retour: %ERRORLEVEL_5%
                if %ERRORLEVEL_5% == 0 (
                    echo Impression réussie avec imprimante par défaut!
                ) else (
                    echo Échec de l'impression avec imprimante par défaut (code %ERRORLEVEL_5%)
                    echo.
                    echo Toutes les tentatives ont échoué.
                )
            )
        )
    )
)

echo.
echo ========== RÉSULTAT FINAL ==========
if %ERRORLEVEL_1% == 0 (
    echo Impression réussie avec la commande standard!
    set FINAL_CODE=0
) else if %ERRORLEVEL_2% == 0 (
    echo Impression réussie avec guillemets simples!
    set FINAL_CODE=0
) else if %ERRORLEVEL_3% == 0 (
    echo Impression réussie sans guillemets!
    set FINAL_CODE=0
) else if %ERRORLEVEL_4% == 0 (
    echo Impression réussie avec option -s!
    set FINAL_CODE=0
) else if %ERRORLEVEL_5% == 0 (
    echo Impression réussie avec imprimante par défaut!
    set FINAL_CODE=0
) else (
    echo ERREUR: Toutes les tentatives d'impression ont échoué.
    set FINAL_CODE=1
)
echo ====================================
echo.

REM Pause pour voir les informations
echo Appuyez sur une touche pour fermer cette fenêtre...
pause > nul
