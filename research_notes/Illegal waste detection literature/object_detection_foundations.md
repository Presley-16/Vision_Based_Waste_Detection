# Foundations of Deep-Learning Object Detection, Evaluation Metrics, and Small-Dataset Training (state as of Nov 2026)

Verification legend used below:
- **[V-web]**: title, authors, year, venue and DOI/arXiv ID checked against a live primary or bibliographic record during this research session (Nov 2026).
- **[V-std]**: a canonical, very widely cited record whose bibliographic details are given from the standard published record. It was not re-fetched this session (tool budget), so the student should click each DOI once before submission.
- **UNVERIFIED**: could not be confirmed. Do not cite without checking.

Context: an MSc project that fine-tunes Ultralytics YOLO11 from COCO-pretrained weights as a single-class "waste" detector on about 3,700 images. The images are Roboflow sets plus the student's own Zimbabwe photos, plus 971 background (no-waste) images, 800 of which are from COCO.

---

## Key Question 1: Seminal and current detectors (CNN background, two-stage, one-stage, YOLO lineage to YOLO26, transformers, surveys)

### Takeaway
Detection moved from CNN classifiers (LeCun 1998, AlexNet 2012) to two-stage region-based detectors (R-CNN, then Fast and Faster R-CNN). It then moved to one-stage dense detectors (YOLO, SSD, RetinaNet with FPN) and finally to NMS-free end-to-end designs (DETR, RT-DETR, YOLOv10, YOLO26). YOLO11 (Sept 2024) was superseded in the Ultralytics line by YOLO26, released in January 2026, with an official paper (arXiv:2606.03748, June 2026). YOLO11 is still a well-documented, defensible baseline: YOLO11n reaches 39.5 COCO mAP50-95 at 1.5 ms on a T4.

### Cited Findings (annotated bibliography, Harvard style)

**CNN background**
- **LeCun, Y., Bottou, L., Bengio, Y. and Haffner, P. (1998) 'Gradient-based learning applied to document recognition', *Proceedings of the IEEE*, 86(11), pp. 2278–2324. doi:10.1109/5.726791. [V-std]** Introduced LeNet-5 and showed that convolutional networks trained end-to-end with back-propagation beat hand-engineered features on handwritten digit recognition (MNIST). This is the base CNN reference. — [DOI](https://doi.org/10.1109/5.726791)
- **Krizhevsky, A., Sutskever, I. and Hinton, G.E. (2012) 'ImageNet classification with deep convolutional neural networks', *Advances in Neural Information Processing Systems 25 (NIPS 2012)*, pp. 1097–1105. Journal version: *Communications of the ACM*, 60(6), pp. 84–90 (2017), doi:10.1145/3065386. [V-std]** AlexNet won ILSVRC-2012 with a 15.3% top-5 test error, against 26.2% for the runner-up. It used ReLU, dropout and GPU training, and it started the deep-learning era in vision. — [DOI](https://doi.org/10.1145/3065386)

**Two-stage detectors**
- **Girshick, R., Donahue, J., Darrell, T. and Malik, J. (2014) 'Rich feature hierarchies for accurate object detection and semantic segmentation', *Proc. IEEE CVPR*, pp. 580–587. doi:10.1109/CVPR.2014.81. arXiv:1311.2524. [V-std]** R-CNN classified CNN features of about 2,000 selective-search region proposals. It reached 53.3% mAP on PASCAL VOC 2012, more than 30% relative above the previous best. It also showed that **ImageNet pre-training followed by fine-tuning on a small detection set** works, which is the direct ancestor of this project's transfer-learning setup. — [arXiv](https://arxiv.org/abs/1311.2524)
- **Girshick, R. (2015) 'Fast R-CNN', *Proc. IEEE ICCV*, pp. 1440–1448. doi:10.1109/ICCV.2015.169. arXiv:1504.08083. [V-std]** Fast R-CNN shared the convolutional computation across proposals through RoI pooling and used a multi-task loss. With VGG16 it trains about 9× faster than R-CNN and tests about 213× faster, with higher mAP (66% on VOC 2012). — [arXiv](https://arxiv.org/abs/1504.08083)
- **Ren, S., He, K., Girshick, R. and Sun, J. (2015) 'Faster R-CNN: Towards real-time object detection with region proposal networks', *NeurIPS 28*. arXiv:1506.01497. Journal version: *IEEE TPAMI*, 39(6), pp. 1137–1149 (2017), doi:10.1109/TPAMI.2016.2577031. [V-std]** Faster R-CNN replaced selective search with a learned Region Proposal Network and introduced **anchor boxes**. It runs at about 5 fps on a GPU with VGG16 and reaches 73.2% mAP on VOC 2007. — [arXiv](https://arxiv.org/abs/1506.01497)

**One-stage detectors**
- **Redmon, J., Divvala, S., Girshick, R. and Farhadi, A. (2016) 'You only look once: Unified, real-time object detection', *Proc. IEEE CVPR*, pp. 779–788. doi:10.1109/CVPR.2016.91. arXiv:1506.02640. [V-std]** YOLO framed detection as a single regression from the whole image to a grid of boxes and class probabilities. It runs at 45 fps with 63.4% mAP on VOC 2007; Fast YOLO runs at 155 fps. It made fewer background false positives than Fast R-CNN but more localisation errors. — [arXiv](https://arxiv.org/abs/1506.02640)
- **Liu, W., Anguelov, D., Erhan, D., Szegedy, C., Reed, S., Fu, C.-Y. and Berg, A.C. (2016) 'SSD: Single shot multibox detector', in *ECCV 2016*, LNCS 9905, pp. 21–37. doi:10.1007/978-3-319-46448-0_2. arXiv:1512.02325. [V-std]** SSD made predictions from default boxes on multiple feature maps. SSD300 reaches 74.3% mAP on VOC 2007 at 59 fps, beating Faster R-CNN on both accuracy and speed at that time. It also showed that **data augmentation** (random crops) added about 8.8 mAP. — [arXiv](https://arxiv.org/abs/1512.02325)
- **Redmon, J. and Farhadi, A. (2018) 'YOLOv3: An incremental improvement', arXiv:1804.02767. [V-std]** YOLOv3 used a Darknet-53 backbone with three-scale prediction and logistic class outputs. It reaches 57.9 AP50 on COCO in 51 ms on a Titan X, compared with RetinaNet's 57.5 AP50 in 198 ms. The author also notes that YOLOv3 is weaker on the stricter COCO AP (about 33.0). — [arXiv](https://arxiv.org/abs/1804.02767)
- **Lin, T.-Y., Dollár, P., Girshick, R., He, K., Hariharan, B. and Belongie, S. (2017) 'Feature pyramid networks for object detection', *Proc. IEEE CVPR*, pp. 2117–2125. doi:10.1109/CVPR.2017.106. arXiv:1612.03144. [V-std]** FPN added a top-down pathway with lateral connections that builds semantically strong multi-scale features. Faster R-CNN with FPN reached 36.2 AP on COCO test-dev. FPN and PAN-style necks remain in every modern YOLO, including YOLO11. — [arXiv](https://arxiv.org/abs/1612.03144)
- **Lin, T.-Y., Goyal, P., Girshick, R., He, K. and Dollár, P. (2017) 'Focal loss for dense object detection', *Proc. IEEE ICCV*, pp. 2980–2988. doi:10.1109/ICCV.2017.324. arXiv:1708.02002. [V-std]** This paper identified the extreme foreground/background class imbalance as the main reason one-stage detectors trailed two-stage ones. The focal loss down-weights easy negatives, and RetinaNet (ResNet-101-FPN) reached 39.1 AP on COCO test-dev, beating the two-stage detectors of the time. — [arXiv](https://arxiv.org/abs/1708.02002)
- **Bochkovskiy, A., Wang, C.-Y. and Liao, H.-Y.M. (2020) 'YOLOv4: Optimal speed and accuracy of object detection', arXiv:2004.10934. [V-std]** YOLOv4 introduced **Mosaic augmentation**, which combines four training images into one, along with a "bag of freebies / bag of specials" set (CSPDarknet53, SPP, PAN, CIoU loss). It reached 43.5% AP (65.7% AP50) on COCO at about 65 fps on a Tesla V100. Mosaic is still a default in Ultralytics training. — [arXiv](https://arxiv.org/abs/2004.10934)
- **Wang, C.-Y., Bochkovskiy, A. and Liao, H.-Y.M. (2023) 'YOLOv7: Trainable bag-of-freebies sets new state-of-the-art for real-time object detectors', *Proc. IEEE/CVF CVPR*, pp. 7464–7475. [V-web]** YOLOv7 proposed E-ELAN, model re-parameterisation and coarse-to-fine label assignment. It reports 56.8% AP for the most accurate real-time model, the highest at 30 fps or more on a V100, across a 5–160 fps range. — [CVF Open Access](https://openaccess.thecvf.com/content/CVPR2023/html/Wang_YOLOv7_Trainable_Bag-of-Freebies_Sets_New_State-of-the-Art_for_Real-Time_Object_Detectors_CVPR_2023_paper.html)
- **Jocher, G., Chaurasia, A. and Qiu, J. (2023) *Ultralytics YOLOv8* (Version 8.0.0) [Computer software]. Available at: https://github.com/ultralytics/ultralytics. Licence AGPL-3.0. [V-std]** YOLOv8 is Ultralytics' anchor-free, decoupled-head detector, and it introduced the `ultralytics` Python package used in this project. No peer-reviewed paper exists, so it is cited as software. — [GitHub](https://github.com/ultralytics/ultralytics)
- **Wang, A., Chen, H., Liu, L., Chen, K., Lin, Z., Han, J. and Ding, G. (2024) 'YOLOv10: Real-time end-to-end object detection', *Advances in Neural Information Processing Systems 37 (NeurIPS 2024)*. arXiv:2405.14458. [V-web]** YOLOv10 removed NMS through consistent dual assignments (one-to-many plus one-to-one heads). YOLOv10-S is 1.8× faster than RT-DETR-R18 at similar COCO AP with 2.8× fewer parameters and FLOPs. YOLOv10-B has 46% lower latency than YOLOv9-C at equal accuracy, and the family gains 1.2–1.4 AP over YOLOv8 across N to X. Page numbers in the NeurIPS proceedings were not confirmed. — [NeurIPS PDF](https://proceedings.neurips.cc/paper_files/paper/2024/file/c34ddd05eb089991f06f3c5dc36836e0-Paper-Conference.pdf); [arXiv](https://arxiv.org/abs/2405.14458)
- **Jocher, G. and Qiu, J. (2024) *Ultralytics YOLO11* (Version 11.0.0) [Computer software]. Available at: https://github.com/ultralytics/ultralytics. Licence AGPL-3.0. [V-web]** Released on 27 September 2024. Ultralytics says it has published no formal paper for YOLO11 and that a DOI is pending. COCO results at 640 px:

  | Model | mAP50-95 | CPU ONNX (ms) | T4 TensorRT10 (ms) | Params (M) | FLOPs (B) |
  |---|---|---|---|---|---|
  | YOLO11n | 39.5 | 56.1 | 1.5 | 2.6 | 6.5 |
  | YOLO11s | 47.0 | 90.0 | 2.5 | 9.4 | 21.6 |
  | YOLO11m | 51.5 | 183.2 | 4.7 | 20.1 | 68.1 |
  | YOLO11l | 53.4 | 238.6 | 6.2 | 25.3 | 87.2 |
  | YOLO11x | 54.7 | 462.8 | 11.3 | 56.9 | 195.3 |

  — [Ultralytics docs](https://docs.ultralytics.com/models/yolo11/)
- **Khanam, R. and Hussain, M. (2024) 'YOLOv11: An overview of the key architectural enhancements', arXiv:2410.17725 (submitted 23 Oct 2024). [V-web]** This is the main paper-style description of YOLO11. It analyses the **C3k2** block, **SPPF** and **C2PSA** (convolutional block with parallel spatial attention). It covers the detection, segmentation, pose and OBB tasks across the nano to extra-large sizes. The abstract gives no numeric results, so cite the Ultralytics docs for numbers. — [arXiv](https://arxiv.org/abs/2410.17725)
- **Jocher, G., Qiu, J., Liu, M., Lyu, S., Akyon, F.C. and Kalfaoglu, M.E. (2026) 'Ultralytics YOLO26: Unified real-time end-to-end vision models', arXiv:2606.03748. doi:10.48550/arXiv.2606.03748. [V-web]** This is the official YOLO26 paper. The model was released in January 2026 and the paper posted in June 2026. YOLO26 is built on YOLO11. Its main changes are native **NMS-free** inference through a dual one-to-one head, **removal of DFL**, the **MuSGD** optimiser (an SGD and Muon hybrid), **ProgLoss**, and **STAL** (small-target-aware label assignment). On COCO, YOLO26n scores 40.9 mAP50-95 (40.1 end-to-end) at 38.9 ms CPU ONNX and 1.7 ms T4, and YOLO26x scores 57.5. The docs give the CPU figure as about 43% faster than YOLO11n (56.1 ms). — [Ultralytics docs](https://docs.ultralytics.com/models/yolo26/); [arXiv](https://arxiv.org/abs/2606.03748)
- (Secondary, optional) **Sapkota, R. et al. (2025) 'YOLO26: Key architectural enhancements and performance benchmarking for real-time object detection', arXiv:2509.25164 (v1 29 Sept 2025, revised to v3 Jan 2026). [V-web, partial: the full author list was not checked]** A third-party review that benchmarks YOLO26 on NVIDIA Jetson devices. It is not the official paper. — [arXiv](https://arxiv.org/abs/2509.25164)

**Transformer detectors**
- **Carion, N., Massa, F., Synnaeve, G., Usunier, N., Kirillov, A. and Zagoruyko, S. (2020) 'End-to-end object detection with transformers', in *ECCV 2020*, LNCS 12346, pp. 213–229. doi:10.1007/978-3-030-58452-8_13. arXiv:2005.12872. [V-std]** DETR treats detection as set prediction with Hungarian matching and a transformer encoder-decoder, which removes anchors and NMS. It reaches 42.0 AP on COCO with ResNet-50, comparable to a tuned Faster R-CNN, but it needs about 500 training epochs and is **worse on small objects**. — [arXiv](https://arxiv.org/abs/2005.12872)
- **Zhao, Y., Lv, W., Xu, S., Wei, J., Wang, G., Dang, Q., Liu, Y. and Chen, J. (2024) 'DETRs beat YOLOs on real-time object detection', *Proc. IEEE/CVF CVPR*, pp. 16965–16974. arXiv:2304.08069. [V-web for venue and numbers; page range V-std]** RT-DETR is presented as the first real-time end-to-end detector, using a hybrid encoder and uncertainty-minimal query selection. RT-DETR-R50 and R101 reach 53.1 and 54.3 AP at 108 and 74 fps on a T4. That is 2.2 AP above DINO-R50 at about 21× the fps. A third-party review notes it is 0.5 AP below YOLOv8-L on small objects. — [CVF Open Access](https://openaccess.thecvf.com/content/CVPR2024/html/Zhao_DETRs_Beat_YOLOs_on_Real-time_Object_Detection_CVPR_2024_paper.html)

**Surveys**
- **Terven, J., Córdova-Esparza, D.-M. and Romero-González, J.-A. (2023) 'A comprehensive review of YOLO architectures in computer vision: From YOLOv1 to YOLOv8 and YOLO-NAS', *Machine Learning and Knowledge Extraction*, 5(4), pp. 1680–1716. doi:10.3390/make5040083. arXiv:2304.00501. [V-web]** Traces each YOLO version's backbone, neck, head, loss and training changes from v1 to v8, YOLO-NAS and YOLO with transformers. It is a good single citation for the YOLO history. The arXiv preprint has a different title and only two authors. — [arXiv](https://arxiv.org/abs/2304.00501)
- **Zou, Z., Chen, K., Shi, Z., Guo, Y. and Ye, J. (2023) 'Object detection in 20 years: A survey', *Proceedings of the IEEE*, 111(3), pp. 257–276. doi:10.1109/JPROC.2023.3238524. arXiv:1905.05055. [V-std]** A broad history of detection from Viola-Jones and HOG/DPM to deep detectors, with milestones, datasets and metrics. — [arXiv](https://arxiv.org/abs/1905.05055)

### Inferences
- **Two-stage vs one-stage vs transformer.**
  - Two-stage detectors (R-CNN family) led accuracy until about 2017 but were slow, at roughly 5 fps for Faster R-CNN.
  - One-stage detectors traded accuracy for speed until FPN and focal loss closed the gap (RetinaNet at 39.1 AP).
  - Transformers (DETR) removed hand-designed parts but trained slowly and struggled on small objects, until RT-DETR made them real-time.
  - By 2024–2026 the field had converged: YOLOv10 and YOLO26 borrowed DETR's NMS-free one-to-one matching while keeping CNN efficiency.
  - For a single-class detector meant for smartphones or edge devices, a one-stage YOLO is the efficient choice that the literature supports.
- **Agreements across sources.**
  - Multi-scale features (FPN/PAN) matter for objects of varied size.
  - Pre-training then fine-tuning is standard (R-CNN onwards).
  - Augmentation gives large gains (SSD's +8.8 mAP; YOLOv4's Mosaic).
- **Contradictions and caveats.**
  - "DETRs beat YOLOs" (Zhao 2024) conflicts with YOLOv10's claim of being 1.8× faster than RT-DETR-R18 at similar AP. Each paper benchmarks under its own conditions (TensorRT version, whether NMS time is included, input size), so headline fps figures are not directly comparable.
  - YOLOv3 looks strong on AP50 but weak on AP@[.5:.95]. Which metric you choose changes the ranking (see KQ2).
- **Justifying YOLO11 in a 2026 dissertation.**
  - YOLO26 is now current, and on COCO YOLO26n beats YOLO11n by 1.4 mAP50-95 while running about 43% faster on CPU.
  - YOLO11 is still a mature, documented baseline. The dissertation should acknowledge YOLO26, and ideally either run it as a comparison or explain why it was excluded (for example, the project timeline was fixed before release, or for stability).
  - STAL and NMS-free inference are relevant to small litter items.
- **Citation hygiene.** Ultralytics models (v8, 11) have no peer-reviewed papers, so cite them as software. Pair YOLO11 with Khanam & Hussain for the architecture description and with the docs for numbers. YOLO26 now has an arXiv paper.

### Gaps
- NeurIPS 2024 page numbers for YOLOv10 were not confirmed. Cite the volume and arXiv ID.
- The exact RT-DETR CVPR page range (16965–16974) is from memory and was not shown in a fetched record. Check it on the CVF page.
- The full author list of Sapkota et al. (arXiv:2509.25164) was not retrieved.
- No official peer-reviewed venue for the YOLO26 paper was found (arXiv only as of Nov 2026).
- The YOLO11 DOI is listed as "pending" by Ultralytics. No Zenodo DOI was confirmed.

---

## Key Question 2: Evaluation (PASCAL VOC, COCO, metric surveys, P/R/F1, mAP@0.5 vs mAP@0.5:0.95, image vs instance level, confidence thresholds)

### Takeaway
PASCAL VOC fixed IoU ≥ 0.5 and interpolated AP. COCO averaged AP over IoU 0.50:0.05:0.95 (which rewards precise localisation) and added size-stratified AP. Padilla et al. show that implementation details change reported scores, so the toolkit and settings must be stated. For a single-class waste detector meant for reporting, mAP@0.5 plus precision, recall and F1 at a chosen confidence threshold are the most decision-relevant metrics. Image-level ("is there waste in this photo?") metrics are under-covered in the literature, and the student must define them.

### Cited Findings
- **Everingham, M., Van Gool, L., Williams, C.K.I., Winn, J. and Zisserman, A. (2010) 'The PASCAL Visual Object Classes (VOC) challenge', *International Journal of Computer Vision*, 88(2), pp. 303–338. doi:10.1007/s11263-009-0275-4. [V-std]** Defines the VOC dataset (20 classes) and its detection protocol. A detection counts as a true positive if IoU ≥ 0.5 with an unmatched ground truth, and duplicates count as false positives. AP is the area under the interpolated precision-recall curve (11-point in VOC 2007, all-point from 2010). — [DOI](https://doi.org/10.1007/s11263-009-0275-4)
- **Lin, T.-Y., Maire, M., Belongie, S., Hays, J., Perona, P., Ramanan, D., Dollár, P. and Zitnick, C.L. (2014) 'Microsoft COCO: Common objects in context', in *ECCV 2014*, LNCS 8693, pp. 740–755. doi:10.1007/978-3-319-10602-1_48. arXiv:1405.0312. [V-std]** COCO has 91 object types (80 used for detection), about 328k images and 2.5M labelled instances, with many small objects in cluttered "non-iconic" scenes. Its primary metric, AP averaged over IoU 0.50–0.95, is the "mAP50-95" that Ultralytics reports. **COCO is also the source of the project's pre-trained weights and of 800 of its negative images.** — [arXiv](https://arxiv.org/abs/1405.0312)
- **Padilla, R., Passos, W.L., Dias, T.L.B., Netto, S.L. and da Silva, E.A.B. (2021) 'A comparative analysis of object detection metrics with a companion open-source toolkit', *Electronics*, 10(3), 279. doi:10.3390/electronics10030279. [V-web]** Reviews the metrics used across detection competitions. It shows that **differences in annotation formats and in AP implementations (interpolation, IoU handling) can change results**, and it releases a toolkit covering 15 metrics. — [MDPI](https://www.mdpi.com/2079-9292/10/3/279/html); [toolkit](https://github.com/rafaelpadilla/review_object_detection_metrics)
- **Padilla, R., Netto, S.L. and da Silva, E.A.B. (2020) 'A survey on performance metrics for object-detection algorithms', *Proc. 2020 International Conference on Systems, Signals and Image Processing (IWSSIP)*, pp. 237–242. doi:10.1109/IWSSIP48289.2020.9145130. [UNVERIFIED: details from memory and not confirmed this session; check before citing]** The shorter predecessor to the 2021 Electronics paper, explaining IoU, precision, recall and AP variants.
- **Hoiem, D., Chodpathumwan, Y. and Dai, Q. (2012) 'Diagnosing error in object detectors', in *ECCV 2012*, LNCS 7574, pp. 340–353. doi:10.1007/978-3-642-33712-3_25. [V-std]** Proposes analysing false positives by type (localisation error, confusion with similar classes, confusion with background) rather than relying only on AP. This is directly useful for analysing waste false positives on clean scenes. — [DOI](https://doi.org/10.1007/978-3-642-33712-3_25)
- Ultralytics' own guidance states that background images "are added to a dataset to reduce False Positives (FP)". This ties the evaluation of FPs on negative images to dataset design (see KQ3). — [Ultralytics tips](https://docs.ultralytics.com/yolov5/tutorials/tips_for_best_training_results/)

### Inferences
- **Metric definitions for the Methodology** (standard; supported by Everingham 2010 and Padilla 2021):
  - Precision = TP/(TP+FP).
  - Recall = TP/(TP+FN).
  - F1 = 2PR/(P+R).
  - AP is the area under the P-R curve. With one class, mAP = AP.
  - mAP@0.5 tolerates loose boxes. mAP@0.5:0.95 penalises imprecise boxes.
- **Choosing a headline metric.** Waste piles have vague, subjective extents, so annotators disagree on the boundaries. That makes mAP@0.5 the fairer headline, with mAP@0.5:0.95 reported for comparability with COCO and YOLO papers. This is consistent with the label-noise findings in KQ3 (box noise hurts strict-IoU metrics most).
- **Image-level vs instance-level evaluation.** For a reporting app, the operational question is often image-level: does the photo contain waste?
  - Image-level TP/FP/FN/TN can be defined as "at least one detection above threshold τ".
  - Image-level specificity can then be measured on the 971 negatives, and per-image false-positive rate is the key user-facing metric.
  - Instance-level mAP cannot measure true negatives at all, which is a known limitation of AP.
- **Confidence threshold selection.**
  - AP is threshold-free, but deployment needs a single τ.
  - Common practice is to choose τ on the **validation** set, either at maximum F1 (Ultralytics plots F1-confidence curves) or at a target precision or false-positive rate on negatives.
  - τ should then be applied unchanged to the test set, to avoid optimistic bias.
- **Comparability.** Padilla et al. show that implementations differ. State that metrics come from Ultralytics `val` (COCO-style 101-point interpolation) and avoid comparing raw numbers with papers that used other toolkits.

### Gaps
- I found no strong peer-reviewed source that formally treats **image-level evaluation of object detectors** or **confidence-threshold selection** for deployment. These remain methodological choices the student must justify. A search for "image-level vs instance-level detection evaluation" was not completed within the tool budget.
- The Padilla et al. (2020) IWSSIP paper is UNVERIFIED.
- The claim that Ultralytics uses 101-point interpolation was not confirmed in a fetched page. Check `ultralytics/utils/metrics.py`.

---

## Key Question 3: Training on small, imbalanced or noisy data (transfer learning, augmentation and Mosaic, negative images, label noise, dataset shift, near-duplicate leakage, early stopping)

### Takeaway
Fine-tuning COCO-pretrained YOLO11 is well supported by transfer-learning theory and by detection practice from R-CNN onwards.

- **Augmentation:** Shorten & Khoshgoftaar's survey and YOLOv4's Mosaic are the canonical references.
- **Negative images:** Ultralytics recommends 0–10% background images to cut false positives. This project's 971 of about 3,700 (about 26%) exceeds that heuristic, which needs justifying.
- **Label noise:** class-label errors and spurious boxes degrade mAP sharply. Box-location noise hurts strict-IoU metrics.
- **Dataset bias:** merging Roboflow sets with Zimbabwe photos creates dataset-bias and shift risks (Torralba & Efros). Near-duplicate leakage can inflate test scores (Barz & Denzler found 3.3–10% duplicates in CIFAR test sets).

### Cited Findings
**Transfer learning**
- **Pan, S.J. and Yang, Q. (2010) 'A survey on transfer learning', *IEEE Transactions on Knowledge and Data Engineering*, 22(10), pp. 1345–1359. doi:10.1109/TKDE.2009.191. [V-std]** Formal definitions of domain and task, and a taxonomy (inductive, transductive, unsupervised). Fine-tuning COCO weights for waste is *inductive* transfer: the source and target tasks differ, and labelled target data exist. — [DOI](https://doi.org/10.1109/TKDE.2009.191)
- **Yosinski, J., Clune, J., Bengio, Y. and Lipson, H. (2014) 'How transferable are features in deep neural networks?', *Advances in Neural Information Processing Systems 27 (NIPS 2014)*, pp. 3320–3328. arXiv:1411.1792. [V-std]** Early layers learn general (Gabor-like) features and later layers become task-specific. Transferability falls as source and target tasks diverge, but **initialising from transferred weights and fine-tuning improved generalisation even on a large target set**, and the boost persisted after fine-tuning. — [arXiv](https://arxiv.org/abs/1411.1792)

**Data augmentation**
- **Shorten, C. and Khoshgoftaar, T.M. (2019) 'A survey on image data augmentation for deep learning', *Journal of Big Data*, 6, 60. doi:10.1186/s40537-019-0197-0. [V-std]** Surveys geometric and photometric transforms, mixing, random erasing, GAN-based and neural style augmentation, and meta-learning augmentation as remedies for overfitting on limited data. It notes that label-preserving safety and test-time augmentation need care. — [DOI](https://doi.org/10.1186/s40537-019-0197-0)
- Bochkovskiy et al. (2020), YOLOv4 (above), introduced Mosaic, which mixes four images so that objects appear in varied contexts and scales, reducing reliance on large mini-batches. [V-std] — [arXiv](https://arxiv.org/abs/2004.10934)

**Background (negative) images and data quantity**
- Ultralytics recommends **"about 0-10% background images to help reduce FPs"**. Background images need no labels. The same page recommends **≥1,500 images and ≥10,000 instances per class**, says that **"partial labeling will not work"** (every instance must be labelled), recommends pre-trained weights for small and medium datasets, and suggests starting at 300 epochs. — [Ultralytics tips](https://docs.ultralytics.com/yolov5/tutorials/tips_for_best_training_results/)
- Lin et al. (2017), focal loss (above): dense detectors already see extreme foreground/background imbalance at the anchor or location level. Adding whole negative images changes **image-level** coverage of hard negatives, such as clean streets and rubble-like textures, rather than location-level imbalance. — [arXiv](https://arxiv.org/abs/1708.02002)

**Label noise in detection**
- **Li, J., Xiong, C., Socher, R. and Hoi, S. (2020) 'Towards noise-resistant object detection with noisy annotations', arXiv:2003.01285. [V-web; no peer-reviewed venue confirmed]** On VOC 2007 with 40% simulated box noise, a vanilla detector's mAP@0.5 fell from 75.5 to 59.3. Their correction method recovered it to 67.8. At 40% noise the mean IoU between noisy and clean boxes is only 0.45. — [arXiv](https://arxiv.org/abs/2003.01285)
- **Chachuła, K., Łyskawa, J., Olber, B., Frątczak, P., Popowicz, A. and Radlak, K. (2023) 'Combating noisy labels in object detection datasets', arXiv:2211.13993 (v3, Dec 2023). [V-web]** Uniform class-label noise was the most harmful, followed by **spurious boxes** and **missing boxes**. Location and scale noise (25% of box size) mattered least. Cleaning datasets with their CLOD method's confident suggestions improved mAP by 16–46%. — [arXiv](https://arxiv.org/abs/2211.13993)

**Dataset bias, shift and generalisation**
- **Torralba, A. and Efros, A.A. (2011) 'Unbiased look at dataset bias', *Proc. IEEE CVPR*, pp. 1521–1528. doi:10.1109/CVPR.2011.5995347. [V-std]** Classifiers could identify which dataset an image came from well above chance ("Name That Dataset"). Cross-dataset tests showed large performance drops, revealing selection, capture and label biases. — [DOI](https://doi.org/10.1109/CVPR.2011.5995347)
- **Recht, B., Roelofs, R., Schmidt, L. and Shankar, V. (2019) 'Do ImageNet classifiers generalize to ImageNet?', *Proc. 36th ICML*, PMLR 97, pp. 5389–5400. arXiv:1902.10811. [V-std]** Models tested on new test sets, collected by replicating the original procedure, lost 3–15% accuracy on CIFAR-10 and 11–14% on ImageNet. Even subtle collection shift hurts. — [arXiv](https://arxiv.org/abs/1902.10811)

**Near-duplicate leakage**
- **Barz, B. and Denzler, J. (2020) 'Do we train on test data? Purging CIFAR of near-duplicates', *Journal of Imaging*, 6(6), 41. doi:10.3390/jimaging6060041. arXiv:1902.00423. [V-web]** About 3.3% of CIFAR-10 and 10% of CIFAR-100 test images had near-duplicates in training. On the cleaned "ciFAIR" test sets, the authors report a relative accuracy drop of roughly 9–14%. They found the duplicates by nearest-neighbour retrieval in CNN feature space. — [PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8321059/)

**Early stopping**
- **Prechelt, L. (1998) 'Early stopping — but when?', in Orr, G.B. and Müller, K.-R. (eds) *Neural Networks: Tricks of the Trade*. LNCS 1524. Berlin: Springer, pp. 55–69. doi:10.1007/3-540-49430-8_3. [V-std]** An empirical comparison of validation-based stopping criteria. Slower criteria gave small generalisation gains (about 4%) at a much higher training-time cost (about 4×). Ultralytics' `patience` parameter implements this idea on validation fitness. — [DOI](https://doi.org/10.1007/3-540-49430-8_3)

### Inferences
- **About 26% negatives versus the 0–10% heuristic.** The Ultralytics figure is an informal guideline, not an empirical study. A higher ratio may suppress false positives on clean scenes but can cost recall. The dissertation should either run an ablation (for example 0%, 10% and 26% negatives, comparing recall and image-level FPR) or frame the choice explicitly as prioritising precision for a reporting app.
- **COCO negatives are also a shift.** The 800 COCO negatives come from a different distribution (Western, iconic-ish scenes) from the Zimbabwe photos. Following Torralba & Efros, the model could learn "COCO style means no waste" as a shortcut. Prefer negatives from the deployment domain (Zimbabwean clean streets and verges), or report results separately on Zimbabwe-only test images.
- **Merged Roboflow sources.** These carry inconsistent labelling conventions: one box per pile versus per item, and missed items. This is exactly the "spurious or missing boxes" noise that Chachuła et al. found harmful, and it breaks Ultralytics' "label every instance" rule. A label audit or harmonisation step is justified.
- **Leakage.** Roboflow exports often include augmented copies and burst or near-identical frames. Per Barz & Denzler, perceptual-hash or embedding-based de-duplication *before* the train/val/test split (or a split grouped by source and location) is needed, otherwise test mAP is inflated.
- **Data quantity.** About 2,700 positive images is above the 1,500-image Ultralytics minimum, but probably below 10,000 instances. Transfer learning (Yosinski; R-CNN) is the standard mitigation, and smaller model sizes (n/s) reduce overfitting risk.
- **Augmentation and stopping.** Mosaic and HSV/flip augmentations are on by default in Ultralytics. Early stopping on validation mAP with `patience` and a held-out test set used only once follows Prechelt.

### Gaps
- **No peer-reviewed empirical study was found that quantifies the optimal proportion of background images for YOLO-family detectors.** The 0–10% figure is only an Ultralytics guideline.
- No detection-specific near-duplicate leakage study was found (Barz & Denzler is about classification on CIFAR). The principle transfers, but no detection numbers are available.
- Domain-generalisation literature specific to detection (for example, domain-adaptive Faster R-CNN, Chen et al., CVPR 2018) was not verified within the tool budget. Add it if the dissertation discusses cross-region shift in depth.
- The Li et al. (2020) noisy-annotation paper has no confirmed peer-reviewed venue (arXiv only on the abstract page).
- Bibliographic details marked [V-std] (about 20 entries) come from canonical records and were not re-fetched this session. Each DOI should be clicked once before submission. All [V-web] entries (11 sources: YOLOv7, YOLOv10, YOLO11 docs, Khanam & Hussain, YOLO26 docs/arXiv, Sapkota, RT-DETR, Terven, Padilla 2021, Barz & Denzler, Li 2020, Chachuła 2023, Ultralytics tips) were confirmed live.
