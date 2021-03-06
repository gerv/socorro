/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

<?php
/**
 * This controller displays various static info about the Socorro system
 */
class About_Controller extends Controller {

   /**
    * In about:crashes a link to this page is created for throttled
    * crash reports.
    */
    public function throttling() {
        cachecontrol::set(array(
  	  'expires' => time() + (60 * 30) // 30 minutes
        ));
    }
}
