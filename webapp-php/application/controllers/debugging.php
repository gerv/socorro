/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

<?php
/**
 * This controller is for debugging stage or production ONLY
 * ***NOTE*** should be empty most of the time. Don't leave any
 * wacky code in the tree, which could become an exploit.
 */
class Debugging_Controller extends Controller {

    /**
     * Default status dashboard nagios can hit up for data.
     */
    public function index() {
	$this->auto_render = false;
	echo "Nothing to see here... move along\n";
    }
}
