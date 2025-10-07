import java.io.File;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.util.ArrayList;
import java.util.List;
import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import org.json.JSONArray;
import org.json.JSONObject;
import com.comsol.model.Model;
import com.comsol.model.util.*;

public class SimRun {

    public record Configuration(
        double initialEigenvalueSearch,
        double largeStep,
        double smallStep,
        int maxIterations,
        String numberOfEigenValues,
        String modelPath,
        String imagesDir,
        String solvedModelPath,
        String pythonExecutablePath,
        String scriptPath,
        File pythonDir
    ) {}

    public static void main(String[] args) {
        // --- CONFIGURATION ---
        Configuration config = new Configuration(
            1.200,    // initialEigenvalueSearch
            0.035,     // largeStep
            0.007,    // smallStep
            15,       // maxIterations
            "4",      // numberOfEigenValues
            "C:\\Users\\mhmdh\\OneDrive\\Desktop\\optics-sensor-research\\NN_NewComsol.mph",
            "C:\\Users\\mhmdh\\OneDrive\\Desktop\\optics-sensor-research\\images",
            "C:\\Users\\mhmdh\\OneDrive\\Desktop\\optics-sensor-research\\solved\\NN_NewComsol_Optimized.mph",
            "C:\\Users\\mhmdh\\OneDrive\\Desktop\\optics-sensor-research\\CNN\\.venv\\Scripts\\python.exe",
            "C:\\Users\\mhmdh\\OneDrive\\Desktop\\optics-sensor-research\\CNN\\categorize.py",
            new File("C:\\Users\\mhmdh\\OneDrive\\Desktop\\optics-sensor-research\\CNN")
        );
        
        Model model = null;
        try {
            model = initializeAndLoadModel(config.modelPath);
            runOptimizationLoop(model, config);
        } catch (Exception e) {
            System.err.println("A fatal error occurred in the main process: " + e.getMessage());
            e.printStackTrace();
        } finally {
            if (model != null) {
                System.out.println("Disconnecting and shutting down engine.");
                ModelUtil.disconnect();
            }
        }
    }

    /**
     * Loop that looks for fundamental mode.
     */
    public static void runOptimizationLoop(Model model, Configuration config) throws Exception {
        ComplexNumber fundamentalModeEigenvalue = null;
        double currentEigenvalueSearch = config.initialEigenvalueSearch;
        double currentStep = config.largeStep;
        int previousDirection = 0;

        for (int iteration = 1; iteration <= config.maxIterations; iteration++) {
            System.out.printf("\n==================== ITERATION #%d / %d ====================\n", iteration, config.maxIterations);

            runSimulationAndExport(model, currentEigenvalueSearch, config.numberOfEigenValues, config.imagesDir);
            List<String> predictions = runPrediction(config);

            // --- Analysis Logic ---
            int fundamentalCount = 0;
            int higherCount = 0;
            int lowerCount = 0;
            int firstFundamentalIndex = -1;

            for (int i = 0; i < predictions.size(); i++) {
                String p = predictions.get(i);
                if (p.equals("fundamental")) {
                    fundamentalCount++;
                    if (firstFundamentalIndex == -1) {
                        firstFundamentalIndex = i;
                    }
                } else if (p.equals("higher")) {
                    higherCount++;
                } else if (p.equals("lower")) {
                    lowerCount++;
                }
            }
            // Simulation output should have two fundamental modes, if only 1 was detected.. means model mistakenly labeled a fundamental mode.
            if (fundamentalCount == 2) {
                System.out.println("\nSUCCESS: Found exactly two fundamental modes! Stopping optimization.");
                String tempOutputFile = config.imagesDir + "\\effectiveModeIndexes.txt";
                fundamentalModeEigenvalue = getEigenvalueFromFileByIndex(tempOutputFile, firstFundamentalIndex);
                break;
            } 
            
            System.out.println("\nINFO: Did not find a pair of fundamental modes. Analyzing results for next step.");
            

            // Change direction based on lower or higher returned
            int currentDirection = 0;
            if (higherCount > lowerCount) {
                currentDirection = -1;
            } else if (lowerCount > higherCount) {
                currentDirection = 1;
            }
            
            // Standard adaptive step logic
            if (currentDirection != 0 && (currentDirection == -previousDirection)) {
                if (currentStep == config.largeStep) {
                    System.out.println("----> OVERSHOT TARGET! Switching from large steps to small steps.");
                    currentStep = config.smallStep;
                }
            }
            
            if (currentDirection == 0) {
                 System.out.println("----> Ambiguous result. Keeping search value the same for next iteration.");
            } else {
                 System.out.printf("----> Adjusting search value. Old: %.4f, Step: %.4f, New: %.4f\n", 
                                   currentEigenvalueSearch, (currentDirection * currentStep), (currentEigenvalueSearch + currentDirection * currentStep));
                 currentEigenvalueSearch += currentDirection * currentStep;
            }
            
            if (currentDirection != 0) {
                previousDirection = currentDirection;
            }

            if (iteration == config.maxIterations) {
                System.out.println("\nFAILURE: Reached max iterations without finding the fundamental mode pair.");
            }
        }

        if (fundamentalModeEigenvalue != null) {
            System.out.println("\n==================== OPTIMIZATION COMPLETE ====================");
            System.out.println("Fundamental Mode Eigenvalue: " + fundamentalModeEigenvalue);
            System.out.println("Found at search parameter value: " + currentEigenvalueSearch);
            System.out.println("\nSaving final solved model to: " + config.solvedModelPath);
            model.save(config.solvedModelPath);
            System.out.println("Model saved.");
        }
    }

    /**
     * Initializes the COMSOL engine and loads the model file.
     */
    public static Model initializeAndLoadModel(String modelPath) {
        try {
            System.out.println("Starting COMSOL engine...");
            ModelUtil.initStandalone(false);
            System.out.println("Engine launched.");
            System.out.println("Loading model: " + modelPath);
            Model model = ModelUtil.load("MyModelTag", modelPath);
            System.out.println("Model loaded successfully.");
            return model;
        } catch (IOException e) {
            System.err.println("❌ Failed to load model: " + e.getMessage());
            e.printStackTrace();
            return null;
        }
    }

    /**
     * Sets parameters, runs the solver, and exports result images.
     */
    public static void runSimulationAndExport(Model model, double currentShift, String numEigs, String imagesDir) {
        System.out.printf("Setting 'Search for eigenvalues around' to: %.4f\n", currentShift);
        model.sol("sol1").feature("e1").set("shift", String.valueOf(currentShift));
        model.sol("sol1").feature("e1").set("neigs", numEigs);
        
        System.out.println("Running solver (sol1)...");
        model.sol("sol1").runAll();
        System.out.println("Solver run complete.");
        
        System.out.println("--- Exporting plots for all available modes ---");
        int plotsExported = 0;
        for (int i = 1; i < 1000; i++) {
            try {
                model.result("pg1").set("looplevel", i);
                String imageOutputPath = String.format("%s\\mode_plot_%d.png", imagesDir, i);
                model.result().export("img1").set("filename", imageOutputPath);
                model.result().export("img1").run();
                plotsExported++;
            } catch (Exception e) {
                break; 
            }
        }
        System.out.println("Exported " + plotsExported + " plots.");
    }

    /**
     * HTTP request to the CNN MODEL server.
     */
    public static List<String> runPrediction(Configuration config) throws java.io.IOException, InterruptedException {
        System.out.println("\n--- Sending prediction request to Python server ---");
        
        HttpClient client = HttpClient.newHttpClient();
        String jsonBody = "{\"image_dir\": \"" + config.imagesDir.replace("\\", "\\\\") + "\"}";

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create("http://127.0.0.1:5000/predict"))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(jsonBody))
                .build();

        HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
        
        System.out.println("Python Server Response (Status Code " + response.statusCode() + "):");
        String responseBody = response.body();

        // --- PRETTY-PRINT JSON ---
        JSONArray jsonArray = new JSONArray(responseBody);
        System.out.println(jsonArray.toString(4));

        // --- PARSE ---
        List<String> predictions = new ArrayList<>();
        for (int i = 0; i < jsonArray.length(); i++) {
            JSONObject obj = jsonArray.getJSONObject(i);
            if (obj.has("prediction")) {
                predictions.add(obj.getString("prediction"));
            }
        }
        
        System.out.println("Python script finished. Parsed " + predictions.size() + " predictions.");
        return predictions;
    }
    
    public record ComplexNumber(double real, double imag) {
        @Override
        public String toString() {
            return String.format("%.4f + (%.7f)i", real, imag);
        }
    }
    
    /**
     * Reads the exported data file to get the eigenvalue for a mode index.
     * @param filePath Path to the text file generated by COMSOL.
     * @param modeIndex The index of the mode to fetch.
     * @return ComplexNumber object for the mode.
     */
    public static ComplexNumber getEigenvalueFromFileByIndex(String filePath, int modeIndex) throws java.io.IOException {
        File file = new File(filePath);
        try (java.util.Scanner scanner = new java.util.Scanner(file)) {
            while (scanner.hasNextLine()) {
                String line = scanner.nextLine();
                if (line.startsWith("%")) continue;

                String[] parts = line.trim().split("\\s+");
                int columnIndex = modeIndex + 2; // +2 to skip X and Y columns...
                
                if (parts.length > columnIndex) {
                    String complexStr = parts[columnIndex].replace("i", "");

                    int splitIndex = -1;

                    for (int j = complexStr.length() - 1; j > 0; j--) {
                        char c = complexStr.charAt(j);
                        if (c == '+' || c == '-') {
                            char charBefore = Character.toUpperCase(complexStr.charAt(j - 1));
                            if (charBefore != 'E') {
                                splitIndex = j;
                                break;
                            }
                        }
                    }
                    
                    if (splitIndex > 0) {
                        String realPartStr = complexStr.substring(0, splitIndex);
                        String imagPartStr = complexStr.substring(splitIndex);
                        
                        double realPart = Double.parseDouble(realPartStr);
                        double imagPart = Double.parseDouble(imagPartStr);
                        
                        return new ComplexNumber(realPart, imagPart);
                    } else {
                        return new ComplexNumber(Double.parseDouble(complexStr), 0.0);
                    }
                }
                break;
            }
        }
        throw new java.io.IOException("Could not find or parse eigenvalue data for mode index " + modeIndex);
    }
}