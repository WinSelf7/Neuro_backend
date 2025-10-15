# Quantization with AWQ

1.  Install the required packages.
    ```bash
    pip install datasets
    ```
2.  If you directly proceed to the third step, you may encounter the following problems:
    ```bash
    RuntimeError: Currently, quantification and calibration of Qwen2_5_VLTextModel are not supported.
    The supported model types are InternLMForCausalLM, InternLM2ForCausalLM, InternLM3ForCausalLM, QWenLMHeadModel, Qwen2ForCausalLM, Qwen3ForCausalLM, BaiChuanForCausalLM, BaichuanForCausalLM, LlamaForCausalLM, LlavaLlamaForCausalLM,MGMLlamaForCausalLM, InternLMXComposer2ForCausalLM, Phi3ForCausalLM, ChatGLMForConditionalGeneration, MixtralForCausalLM, Qwen2VLForConditionalGeneration, Qwen2_5_VLForConditionalGeneration, MistralForCausalLM.
    ```
    This is because in the calibrte.py file of the lmdeploy library, the following code (lines 255-258) replaces `model` with `vl_model.language_model`, causing `model_type` to become `Qwen2_5_VLTextModel` instead of the supported `Qwen2_5_VLForConditionalGeneration`:
    ```
    if hasattr(vl_model, 'language_model'):  # deepseek-vl, ...
        model = vl_model.language_model
    if hasattr(vl_model, 'llm'):  # MiniCPMV, ...
        model = vl_model.llm
    ```
    Find these codes and comment out these lines:
    ```
    # if hasattr(vl_model, 'language_model'):  # deepseek-vl, ...
    #     model = vl_model.language_model
    # if hasattr(vl_model, 'llm'):  # MiniCPMV, ...
    #     model = vl_model.llm
    ```    
    You can use the following command to view the directory of the **lmdeploy** library:
    ```bash    
    python -c "import lmdeploy; import os; print(os.path.dirname(lmdeploy.__file__))"
    ```    
    The relative location of calibrte.py is in **lmdeploy/lite/apis/calibrate.py**

    Or you can download [tools/fix_qwen2_5_vl_awq.py](https://github.com/Yuliang-Liu/MonkeyOCR/blob/main/tools/fix_qwen2_5_vl_awq.py)

    Run in your environment:
    ```bash
    python tools/fix_qwen2_5_vl_awq.py patch
    ```
    **Note**: This command modifies LMDeploy’s source code in your environment. To undo the changes, simply run:
    ```bash
    python tools/fix_qwen2_5_vl_awq.py restore
    ```
    
4.  Enter the following in the terminal.
    ```bash
    lmdeploy lite auto_awq \
        ./model_weight/Recognition \
        --calib-dataset 'ptb' \
        --calib-samples 64 \
        --calib-seqlen 1024 \
        --w-bits 4 \
        --w-group-size 128 \
        --batch-size 1 \
        --work-dir ./monkeyocr_quantization
    ```
    Wait for the quantization to complete.
    * If the quantization process is killed, you need to check if you have sufficient memory.
    * For reference, the maximum VRAM usage for quantization with these parameters is approximately 6.47GB.

5.  You might encounter the following error:
    ```
    RuntimeError: Error(s) in loading state_dict for Linear:
        size mismatch for bias: copying a param with shape torch.Size([2048]) from checkpoint, the shape in current model is torch.Size([1280]).
    ```
    This is because your installed version of LMDeploy is not yet compatible with Qwen2.5VL. You need to install the latest development version from the GitHub repository.
    ```bash
    pip install git+https://github.com/InternLM/lmdeploy.git
    ```
    After the installation is complete, try quantizing again.

6.  After quantization is complete, replace the `Recognition` folder.
    ```bash
    mv model_weight/Recognition Recognition_backup

    mv monkeyocr_quantization model_weight/Recognition
    ```
    Then, you can try running the program again.
