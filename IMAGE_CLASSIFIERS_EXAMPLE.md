# Using the Image Classifier Functionality
1. We can start by setting up our model, we’ve used HuggingFace InferenceEndpoints as they are straightforward to set up. We’ve chosen a ViT-based MNIST model for demonstration purposes.

<h2 align="center">
  <img src="https://github.com/Mindgard/public-resources/blob/main/cliimagemodels/hf.png?raw=true"/>
</h2>

2. We also need to provide an API key for accessing our model from step 1.This authorization step isn’t necessary if you are hosting your own AI model.

<h2 align="center">
  <img src="https://github.com/Mindgard/public-resources/blob/main/cliimagemodels/ats.png?raw=true"/>
</h2>

3. Next, we install the `mindgard` package using `pip`.

<h2 align="center">
  <img src="https://github.com/Mindgard/public-resources/blob/main/cliimagemodels/pipinstallmindgard.gif?raw=true"/>
</h2>

4. We can then login via the `mindgard login` command.

<h2 align="center">
  <img src="https://github.com/Mindgard/public-resources/blob/main/cliimagemodels/login.gif?raw=true"/>
</h2>

5. We define our target model configuration using a `toml` file. We’ve used the URL from our hosted HuggingFace model from step 1, and the API key generated within step 2. We set model type as ‘image’, testing dataset to ‘mnist’, and configure the image labels to expect from our model. We have a suite of additional datasets available to use, so pick one best suited to your model's task! More about labels and datasets are available on our GitHub. If you're hosting your image model on HuggingFace, the labels for many models can be copied from the [config.json 'id2label' field](https://huggingface.co/nateraw/vit-base-beans/blob/main/config.json).

<h2 align="center">
  <img src="https://github.com/Mindgard/public-resources/blob/main/cliimagemodels/config.gif?raw=true"/>
</h2>

6. Use the `mindgard test –config=image-model.toml` to begin running your security tests. Attack speed is dependent on the inference speed of your target model, and how fast the attacks converge on an answer based on your model’s prediction accuracy. Your custom model may vary, but for our MNIST example, expect this process to take a few minutes.

<h2 align="center">
  <img src="https://github.com/Mindgard/public-resources/blob/main/cliimagemodels/test.gif?raw=true"/>
</h2>

7. Once the attacks have completed, security risk scores of your AI model are presented within the terminal, and a URL is generated that navigates to detailed results within your Internet browser. In the AI risk report given below, you can see that the VIT-based MNIST model exhibits a high risk score when exposed to SquareAttack (80%), and BoundaryAttack (100%), indicating high security vulnerabilities against evasion attacks. The risk threshold that defines pass or fail was set to 50%, meaning that the AI model’s deployment within an MLOPs pipeline would have halted.

<h2 align="center">
  <img src="https://github.com/Mindgard/public-resources/blob/main/cliimagemodels/results.gif?raw=true"/>
</h2>

Extra details can be found in the README covering [API compatability](https://github.com/Mindgard/cli/blob/main/README.md#image-classifier-api), [datasets](https://github.com/Mindgard/cli/blob/main/README.md#datasets) and [labels](https://github.com/Mindgard/cli/blob/main/README.md#labels).
